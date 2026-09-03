import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.db import videos_collection
from app.models import SyncRequest, TranscriptResponse, TranscriptSegment, Video
from app.services import storage_service
from app.services.transcript_service import (
    TranscriptUnavailableError,
    fetch_transcript_segments,
    filter_segments,
    regenerate_transcript_segments,
    segments_to_text,
)
from app.services.youtube_service import ChannelNotFoundError, fetch_channel, fetch_videos_in_range

router = APIRouter(tags=["videos"])


async def _get_video_or_404(video_id: str) -> dict:
    doc = await videos_collection.find_one({"video_id": video_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
    return doc


@router.post("/channels/{channel_id}/sync", response_model=list[Video])
async def sync_channel_videos(channel_id: str, request: SyncRequest) -> list[Video]:
    try:
        channel_info = fetch_channel(channel_id)
    except ChannelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    fetched = fetch_videos_in_range(
        channel_info["uploads_playlist_id"], request.start_date, request.end_date
    )

    now = datetime.now(timezone.utc)
    results: list[Video] = []
    for item in fetched:
        existing = await videos_collection.find_one({"video_id": item["video_id"]})
        doc = {
            "video_id": item["video_id"],
            "channel_id": channel_id,
            "title": item["title"],
            "description": item["description"],
            "published_at": item["published_at"],
            "thumbnail_url": item["thumbnail_url"],
            "video_type": item["video_type"],
            "transcript_status": existing["transcript_status"] if existing else "none",
            "transcript_s3_key": existing.get("transcript_s3_key") if existing else None,
            "article_status": existing["article_status"] if existing else "none",
            "article_s3_key": existing.get("article_s3_key") if existing else None,
            "created_at": existing["created_at"] if existing else now,
            "updated_at": now,
        }
        await videos_collection.update_one(
            {"video_id": item["video_id"]}, {"$set": doc}, upsert=True
        )
        results.append(Video(**doc))

    return results


@router.get("/videos", response_model=list[Video])
async def list_videos(
    channel_id: str,
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
) -> list[Video]:
    cursor = videos_collection.find(
        {
            "channel_id": channel_id,
            "published_at": {"$gte": start_date, "$lte": end_date},
        },
        {"_id": 0},
    ).sort("published_at", -1)
    docs = await cursor.to_list(length=500)
    return [Video(**doc) for doc in docs]


@router.get("/videos/{video_id}", response_model=Video)
async def get_video(video_id: str) -> Video:
    doc = await _get_video_or_404(video_id)
    doc.pop("_id", None)
    return Video(**doc)


@router.post("/videos/{video_id}/transcript", response_model=Video)
async def fetch_video_transcript(video_id: str) -> Video:
    doc = await _get_video_or_404(video_id)

    try:
        segments = fetch_transcript_segments(video_id)
    except TranscriptUnavailableError:
        await videos_collection.update_one(
            {"video_id": video_id},
            {"$set": {"transcript_status": "unavailable", "updated_at": datetime.now(timezone.utc)}},
        )
        doc = await _get_video_or_404(video_id)
        doc.pop("_id", None)
        return Video(**doc)

    key = storage_service.transcript_key(video_id)
    storage_service.put_json(key, segments)

    await videos_collection.update_one(
        {"video_id": video_id},
        {
            "$set": {
                "transcript_status": "fetched",
                "transcript_s3_key": key,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    doc = await _get_video_or_404(video_id)
    doc.pop("_id", None)
    return Video(**doc)


@router.post("/videos/{video_id}/transcript/regenerate", response_model=Video)
async def regenerate_video_transcript(video_id: str, background_tasks: BackgroundTasks) -> Video:
    await _get_video_or_404(video_id)

    await videos_collection.update_one(
        {"video_id": video_id},
        {"$set": {"transcript_status": "processing", "updated_at": datetime.now(timezone.utc)}},
    )
    background_tasks.add_task(_run_transcript_regeneration, video_id)

    doc = await _get_video_or_404(video_id)
    doc.pop("_id", None)
    return Video(**doc)


async def _run_transcript_regeneration(video_id: str) -> None:
    try:
        segments, languages = await asyncio.to_thread(regenerate_transcript_segments, video_id)
    except Exception:
        await videos_collection.update_one(
            {"video_id": video_id},
            {"$set": {"transcript_status": "unavailable", "updated_at": datetime.now(timezone.utc)}},
        )
        return

    key = storage_service.transcript_key(video_id)
    await asyncio.to_thread(storage_service.put_json, key, segments)

    await videos_collection.update_one(
        {"video_id": video_id},
        {
            "$set": {
                "transcript_status": "fetched",
                "transcript_s3_key": key,
                "transcript_source": "elevenlabs_stt",
                "transcript_languages": languages,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )


@router.get("/videos/{video_id}/transcript", response_model=TranscriptResponse)
async def get_video_transcript(
    video_id: str,
    start_seconds: float | None = Query(None, ge=0),
    end_seconds: float | None = Query(None, ge=0),
) -> TranscriptResponse:
    if start_seconds is not None and end_seconds is not None and start_seconds >= end_seconds:
        raise HTTPException(status_code=400, detail="start_seconds must be less than end_seconds")

    doc = await _get_video_or_404(video_id)
    if doc["transcript_status"] != "fetched" or not doc.get("transcript_s3_key"):
        raise HTTPException(status_code=400, detail="Transcript not fetched yet")
    segments = storage_service.get_json(doc["transcript_s3_key"])
    selected = filter_segments(segments, start_seconds, end_seconds)
    return TranscriptResponse(
        text=segments_to_text(selected),
        segments=[TranscriptSegment(**segment) for segment in selected],
    )
