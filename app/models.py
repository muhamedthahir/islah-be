from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TranscriptStatus = Literal["none", "fetched", "unavailable", "processing"]
TranscriptSource = Literal["youtube_captions", "elevenlabs_stt"]
ArticleStatus = Literal["none", "generated"]
VideoType = Literal["video", "short", "live"]
AudioSource = Literal["upload", "url"]


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
    video_type: VideoType = "video"
    transcript_status: TranscriptStatus = "none"
    transcript_s3_key: str | None = None
    transcript_source: TranscriptSource = "youtube_captions"
    transcript_languages: list[str] = []
    article_status: ArticleStatus = "none"
    article_s3_key: str | None = None
    created_at: datetime
    updated_at: datetime


class Audio(BaseModel):
    audio_id: str
    title: str
    source: AudioSource
    source_url: str | None = None
    s3_key: str | None = None
    content_type: str | None = None
    transcript_status: TranscriptStatus = "none"
    transcript_s3_key: str | None = None
    transcript_languages: list[str] = []
    created_at: datetime
    updated_at: datetime


class AudioUrlRequest(BaseModel):
    url: str
    title: str | None = None


class SyncRequest(BaseModel):
    start_date: datetime
    end_date: datetime


class TextResponse(BaseModel):
    text: str


class TranscriptSegment(BaseModel):
    text: str
    start: float
    duration: float


class TranscriptResponse(BaseModel):
    text: str
    segments: list[TranscriptSegment]
