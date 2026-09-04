from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

_client = AsyncIOMotorClient(settings.mongo_uri)
_db = _client[settings.mongo_db_name]

channels_collection = _db["channels"]
videos_collection = _db["videos"]
audio_collection = _db["audio"]


async def ensure_indexes() -> None:
    await channels_collection.create_index("channel_id", unique=True)
    await videos_collection.create_index("video_id", unique=True)
    await videos_collection.create_index([("channel_id", 1), ("published_at", 1)])
    await audio_collection.create_index("audio_id", unique=True)
