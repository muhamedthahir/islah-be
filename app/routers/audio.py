import asyncio
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile

from app.db import audio_collection
from app.models import Audio, AudioUrlRequest, TranscriptResponse, TranscriptSegment
from app.services import audio_library_service, storage_service, stt_service
from app.services.transcript_service import filter_segments, segments_to_text

router = APIRouter(prefix="/audio", tags=["audio"])


async def _get_audio_or_404(audio_id: str) -> dict:
    doc = await audio_collection.find_one({"audio_id": audio_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Audio {audio_id} not found")
    return doc


@router.get("", response_model=list[Audio])
async def list_audio() -> list[Audio]:
    cursor = audio_collection.find({}, {"_id": 0}).sort("created_at", -1)
    docs = await cursor.to_list(length=500)
    return [Audio(**doc) for doc in docs]


@router.post("", response_model=Audio)
async def upload_audio(
    file: UploadFile = File(...),
    title: str | None = Form(None),
) -> Audio:
    audio_id = uuid.uuid4().hex
    ext = os.path.splitext(file.filename or "")[1]
    data = await file.read()

    key = storage_service.audio_key(audio_id, ext)
    storage_service.put_bytes(key, data, file.content_type or "application/octet-stream")

    now = datetime.now(timezone.utc)
    doc = {
        "audio_id": audio_id,
        "title": title or file.filename or audio_id,
        "source": "upload",
        "source_url": None,
        "s3_key": key,
        "content_type": file.content_type,
        "transcript_status": "none",
        "transcript_s3_key": None,
        "transcript_languages": [],
        "created_at": now,
        "updated_at": now,
    }
    await audio_collection.insert_one(doc)
    doc.pop("_id", None)
    return Audio(**doc)


@router.post("/url", response_model=Audio)
async def add_audio_url(request: AudioUrlRequest) -> Audio:
    audio_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    doc = {
        "audio_id": audio_id,
        "title": request.title or request.url,
        "source": "url",
        "source_url": request.url,
        "s3_key": None,
        "content_type": None,
        "transcript_status": "none",
        "transcript_s3_key": None,
        "transcript_languages": [],
        "created_at": now,
        "updated_at": now,
    }
    await audio_collection.insert_one(doc)
    doc.pop("_id", None)
    return Audio(**doc)


@router.get("/{audio_id}", response_model=Audio)
async def get_audio(audio_id: str) -> Audio:
    doc = await _get_audio_or_404(audio_id)
    doc.pop("_id", None)
    return Audio(**doc)


@router.post("/{audio_id}/transcript/regenerate", response_model=Audio)
async def regenerate_audio_transcript(audio_id: str, background_tasks: BackgroundTasks) -> Audio:
    await _get_audio_or_404(audio_id)

    await audio_collection.update_one(
        {"audio_id": audio_id},
        {"$set": {"transcript_status": "processing", "updated_at": datetime.now(timezone.utc)}},
    )
    background_tasks.add_task(_run_transcript_regeneration, audio_id)

    doc = await _get_audio_or_404(audio_id)
    doc.pop("_id", None)
    return Audio(**doc)


def _transcribe(doc: dict) -> tuple[list[dict], list[str]]:
    path = audio_library_service.get_local_path(doc)
    try:
        segments, languages = stt_service.transcribe_audio(path)
    finally:
        audio_library_service.cleanup(path)
    return [segment.model_dump() for segment in segments], languages


async def _run_transcript_regeneration(audio_id: str) -> None:
    doc = await audio_collection.find_one({"audio_id": audio_id})
    if not doc:
        return

    try:
        segments, languages = await asyncio.to_thread(_transcribe, doc)
    except Exception:
        await audio_collection.update_one(
            {"audio_id": audio_id},
            {"$set": {"transcript_status": "unavailable", "updated_at": datetime.now(timezone.utc)}},
        )
        return

    key = storage_service.audio_transcript_key(audio_id)
    await asyncio.to_thread(storage_service.put_json, key, segments)

    await audio_collection.update_one(
        {"audio_id": audio_id},
        {
            "$set": {
                "transcript_status": "fetched",
                "transcript_s3_key": key,
                "transcript_languages": languages,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )


@router.get("/{audio_id}/transcript", response_model=TranscriptResponse)
async def get_audio_transcript(
    audio_id: str,
    start_seconds: float | None = Query(None, ge=0),
    end_seconds: float | None = Query(None, ge=0),
) -> TranscriptResponse:
    if start_seconds is not None and end_seconds is not None and start_seconds >= end_seconds:
        raise HTTPException(status_code=400, detail="start_seconds must be less than end_seconds")

    doc = await _get_audio_or_404(audio_id)
    if doc["transcript_status"] != "fetched" or not doc.get("transcript_s3_key"):
        raise HTTPException(status_code=400, detail="Transcript not fetched yet")
    segments = storage_service.get_json(doc["transcript_s3_key"])
    selected = filter_segments(segments, start_seconds, end_seconds)
    return TranscriptResponse(
        text=segments_to_text(selected),
        segments=[TranscriptSegment(**segment) for segment in selected],
    )
