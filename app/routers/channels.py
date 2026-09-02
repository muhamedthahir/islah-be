from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import channels_collection
from app.models import Channel
from app.services.youtube_service import ChannelNotFoundError, fetch_channel

router = APIRouter(prefix="/channels", tags=["channels"])


class AddChannelRequest(BaseModel):
    channel_id: str


async def upsert_channel(channel_id: str) -> Channel:
    info = fetch_channel(channel_id)
    doc = {
        "channel_id": info["channel_id"],
        "title": info["title"],
        "thumbnail_url": info["thumbnail_url"],
        "created_at": datetime.now(timezone.utc),
    }
    existing = await channels_collection.find_one({"channel_id": channel_id})
    if existing:
        doc["created_at"] = existing["created_at"]
    await channels_collection.update_one(
        {"channel_id": channel_id}, {"$set": doc}, upsert=True
    )
    return Channel(**doc)


@router.post("", response_model=Channel)
async def add_channel(request: AddChannelRequest) -> Channel:
    try:
        return await upsert_channel(request.channel_id)
    except ChannelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=list[Channel])
async def list_channels() -> list[Channel]:
    docs = await channels_collection.find({}, {"_id": 0}).to_list(length=100)
    return [Channel(**doc) for doc in docs]
