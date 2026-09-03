import re
from datetime import datetime, timezone

from googleapiclient.discovery import build

from app.config import settings

_DURATION_RE = re.compile(
    r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?"
)
_SHORT_MAX_SECONDS = 60


class ChannelNotFoundError(Exception):
    pass


def _client():
    return build("youtube", "v3", developerKey=settings.youtube_api_key)


def _duration_to_seconds(duration: str) -> int:
    match = _DURATION_RE.fullmatch(duration)
    if not match:
        return 0
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return hours * 3600 + minutes * 60 + seconds


def _classify_video_type(snippet: dict, content_details: dict) -> str:
    if snippet.get("liveBroadcastContent") in ("live", "upcoming"):
        return "live"
    duration_seconds = _duration_to_seconds(content_details.get("duration", ""))
    if duration_seconds and duration_seconds <= _SHORT_MAX_SECONDS:
        return "short"
    return "video"


def fetch_video_types(video_ids: list[str]) -> dict[str, str]:
    youtube = _client()
    video_types: dict[str, str] = {}

    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        response = (
            youtube.videos()
            .list(id=",".join(chunk), part="snippet,contentDetails")
            .execute()
        )
        for item in response.get("items", []):
            video_types[item["id"]] = _classify_video_type(
                item.get("snippet", {}), item.get("contentDetails", {})
            )

    return video_types


def fetch_channel(channel_id: str) -> dict:
    youtube = _client()
    response = (
        youtube.channels()
        .list(id=channel_id, part="snippet,contentDetails")
        .execute()
    )
    items = response.get("items", [])
    if not items:
        raise ChannelNotFoundError(f"No YouTube channel found for id={channel_id}")

    item = items[0]
    snippet = item["snippet"]
    return {
        "channel_id": channel_id,
        "title": snippet["title"],
        "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url"),
        "uploads_playlist_id": item["contentDetails"]["relatedPlaylists"]["uploads"],
    }


def fetch_videos_in_range(
    uploads_playlist_id: str, start_date: datetime, end_date: datetime
) -> list[dict]:
    youtube = _client()
    videos: list[dict] = []
    page_token: str | None = None

    while True:
        response = (
            youtube.playlistItems()
            .list(
                playlistId=uploads_playlist_id,
                part="snippet",
                maxResults=50,
                pageToken=page_token,
            )
            .execute()
        )

        stop_paging = False
        for item in response.get("items", []):
            snippet = item["snippet"]
            published_at = datetime.fromisoformat(
                snippet["publishedAt"].replace("Z", "+00:00")
            )

            if published_at < start_date.replace(tzinfo=timezone.utc):
                stop_paging = True
                continue
            if published_at > end_date.replace(tzinfo=timezone.utc):
                continue

            videos.append(
                {
                    "video_id": snippet["resourceId"]["videoId"],
                    "title": snippet["title"],
                    "description": snippet.get("description", ""),
                    "published_at": published_at,
                    "thumbnail_url": snippet.get("thumbnails", {})
                    .get("default", {})
                    .get("url"),
                }
            )

        page_token = response.get("nextPageToken")
        if not page_token or stop_paging:
            break

    video_types = fetch_video_types([video["video_id"] for video in videos])
    for video in videos:
        video["video_type"] = video_types.get(video["video_id"], "video")

    return videos
