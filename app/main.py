import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import ensure_indexes
from app.routers import articles, audio, channels, videos
from app.routers.channels import upsert_channel
from app.services.youtube_service import ChannelNotFoundError

logger = logging.getLogger("app")

app = FastAPI(title="Islah")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(channels.router)
app.include_router(videos.router)
app.include_router(articles.router)
app.include_router(audio.router)


@app.on_event("startup")
async def on_startup() -> None:
    await ensure_indexes()

    if settings.default_channel_id:
        try:
            await upsert_channel(settings.default_channel_id)
        except ChannelNotFoundError:
            logger.warning(
                "DEFAULT_CHANNEL_ID=%s could not be resolved via YouTube API",
                settings.default_channel_id,
            )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
