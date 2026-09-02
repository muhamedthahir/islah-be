from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TranscriptStatus = Literal["none", "fetched", "unavailable"]
ArticleStatus = Literal["none", "generated"]


class Channel(BaseModel):
    channel_id: str
    title: str
    thumbnail_url: str | None = None
    created_at: datetime


class Video(BaseModel):
    video_id: str
    channel_id: str
    title: str
    description: str
    published_at: datetime
    thumbnail_url: str | None = None
    transcript_status: TranscriptStatus = "none"
    transcript_s3_key: str | None = None
    article_status: ArticleStatus = "none"
    article_s3_key: str | None = None
    created_at: datetime
    updated_at: datetime


class SyncRequest(BaseModel):
    start_date: datetime
    end_date: datetime


class TextResponse(BaseModel):
    text: str
