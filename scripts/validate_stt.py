"""
One-off validation tool: run a YouTube video through the real regenerate-transcript
pipeline (audio_service + stt_service) and print the result, so quality can be
eyeballed against known Tamil/Arabic/Urdu code-switched clips before trusting the
feature end-to-end.

Usage:
    python scripts/validate_stt.py VIDEO_ID [VIDEO_ID ...]
"""

import sys

sys.path.insert(0, ".")

from app.services import audio_service, stt_service  # noqa: E402


def validate(video_id: str) -> None:
    print(f"\n=== {video_id} ===")
    file_path = audio_service.download_audio(video_id)
    try:
        segments, languages = stt_service.transcribe_audio(file_path)
    finally:
        audio_service.cleanup_audio(file_path)

    print(f"detected languages: {languages}")
    for segment in segments:
        print(f"[{segment.start:7.2f}s +{segment.duration:5.2f}s] {segment.text}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_stt.py VIDEO_ID [VIDEO_ID ...]")
        sys.exit(1)

    for video_id in sys.argv[1:]:
        validate(video_id)
