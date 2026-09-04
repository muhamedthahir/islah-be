import logging

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import CouldNotRetrieveTranscript

from app.services import audio_service, stt_service

logger = logging.getLogger(__name__)


class TranscriptUnavailableError(Exception):
    pass


def regenerate_transcript_segments(video_id: str) -> tuple[list[dict], list[str]]:
    file_path = audio_service.download_audio(video_id)
    print(file_path)
    try:
        segments, languages = stt_service.transcribe_audio(file_path)
    finally:
        audio_service.cleanup_audio(file_path)

    return [segment.model_dump() for segment in segments], languages


def fetch_transcript_segments(video_id: str) -> list[dict]:
    try:
        transcript_list = YouTubeTranscriptApi().list(video_id)
        transcripts = list(transcript_list)
        transcript = next((t for t in transcripts if not t.is_generated), transcripts[0])
        data = transcript.fetch()
    except CouldNotRetrieveTranscript as exc:
        logger.warning("Transcript fetch failed for %s: %s: %s", video_id, type(exc).__name__, exc)
        raise TranscriptUnavailableError(str(exc)) from exc

    return [
        {"text": snippet.text, "start": snippet.start, "duration": snippet.duration}
        for snippet in data
    ]


def filter_segments(
    segments: list[dict],
    start_seconds: float | None = None,
    end_seconds: float | None = None,
) -> list[dict]:
    if start_seconds is None and end_seconds is None:
        return segments

    lo = start_seconds if start_seconds is not None else 0.0
    hi = end_seconds if end_seconds is not None else float("inf")
    return [
        segment
        for segment in segments
        if segment["start"] < hi and segment["start"] + segment["duration"] > lo
    ]


def segments_to_text(segments: list[dict]) -> str:
    return "\n".join(segment["text"] for segment in segments)
