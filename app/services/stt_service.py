import requests

from app.config import settings
from app.models import TranscriptSegment

SCRIBE_ENDPOINT = "https://api.elevenlabs.io/v1/speech-to-text"
SCRIBE_MODEL_ID = "scribe_v2"
SEGMENT_GAP_SECONDS = 0.75
REQUEST_TIMEOUT_SECONDS = 1800


class TranscriptionError(Exception):
    pass


def transcribe_audio(file_path: str) -> tuple[list[TranscriptSegment], list[str]]:
    with open(file_path, "rb") as audio_file:
        response = requests.post(
            SCRIBE_ENDPOINT,
            headers={"xi-api-key": settings.elevenlabs_api_key},
            data={"model_id": SCRIBE_MODEL_ID},
            files={"file": audio_file},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    if response.status_code != 200:
        raise TranscriptionError(f"ElevenLabs STT failed ({response.status_code}): {response.text}")

    payload = response.json()
    return _to_segments(payload)


def _to_segments(payload: dict) -> tuple[list[TranscriptSegment], list[str]]:
    words = payload.get("words", [])
    default_language = payload.get("language_code")

    segments: list[TranscriptSegment] = []
    languages: set[str] = set()
    current_words: list[str] = []
    current_language: str | None = None
    current_start: float = 0.0
    current_end: float = 0.0

    def flush() -> None:
        if current_words:
            segments.append(
                TranscriptSegment(
                    text=" ".join(current_words).strip(),
                    start=current_start,
                    duration=max(current_end - current_start, 0.0),
                )
            )

    for word in words:
        if word.get("type") == "spacing":
            continue

        text = word.get("text", "")
        start = word.get("start", current_end)
        end = word.get("end", start)
        language = word.get("language_code", default_language)
        if language:
            languages.add(language)

        starts_new_segment = (
            not current_words
            or language != current_language
            or start - current_end > SEGMENT_GAP_SECONDS
        )
        if starts_new_segment:
            flush()
            current_words = []
            current_language = language
            current_start = start

        current_words.append(text)
        current_end = end

    flush()

    if default_language:
        languages.add(default_language)

    return segments, sorted(languages)
