import json

import boto3

from app.config import settings

_s3 = boto3.client(
    "s3",
    region_name=settings.aws_region,
    aws_access_key_id=settings.aws_access_key_id or None,
    aws_secret_access_key=settings.aws_secret_access_key or None,
)


def put_text(key: str, text: str) -> None:
    _s3.put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=text.encode("utf-8"),
        ContentType="text/plain; charset=utf-8",
    )


def get_text(key: str) -> str:
    response = _s3.get_object(Bucket=settings.s3_bucket_name, Key=key)
    return response["Body"].read().decode("utf-8")


def put_bytes(key: str, data: bytes, content_type: str) -> None:
    _s3.put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def get_bytes(key: str) -> bytes:
    response = _s3.get_object(Bucket=settings.s3_bucket_name, Key=key)
    return response["Body"].read()


def put_json(key: str, data: list[dict]) -> None:
    _s3.put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=json.dumps(data).encode("utf-8"),
        ContentType="application/json; charset=utf-8",
    )


def get_json(key: str) -> list[dict]:
    response = _s3.get_object(Bucket=settings.s3_bucket_name, Key=key)
    return json.loads(response["Body"].read().decode("utf-8"))


def transcript_key(video_id: str) -> str:
    return f"transcripts/{video_id}.json"


def article_key(video_id: str) -> str:
    return f"articles/{video_id}.txt"


def audio_key(audio_id: str, ext: str) -> str:
    return f"{settings.audio_s3_prefix}/files/{audio_id}{ext}"


def audio_transcript_key(audio_id: str) -> str:
    return f"{settings.audio_s3_prefix}/transcripts/{audio_id}.json"
