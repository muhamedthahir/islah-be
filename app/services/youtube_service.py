from datetime import datetime, timezone

from googleapiclient.discovery import build

from app.config import settings


class ChannelNotFoundError(Exception):
    pass


def _client():
    return build("youtube", "v3", developerKey=settings.youtube_api_key)


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

    return videos
