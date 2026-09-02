from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.db import videos_collection
from app.models import TextResponse, Video
from app.services import storage_service
from app.services.anthropic_service import generate_article

router = APIRouter(tags=["articles"])


async def _get_video_or_404(video_id: str) -> dict:
    doc = await videos_collection.find_one({"video_id": video_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
    return doc


@router.post("/videos/{video_id}/article", response_model=Video)
async def generate_video_article(video_id: str) -> Video:
    doc = await _get_video_or_404(video_id)
    if doc["transcript_status"] != "fetched" or not doc.get("transcript_s3_key"):
        raise HTTPException(status_code=400, detail="Transcript not fetched yet")

    transcript_text = storage_service.get_text(doc["transcript_s3_key"])
    article_text = generate_article(doc["title"], transcript_text)

    key = storage_service.article_key(video_id)
    storage_service.put_text(key, article_text)

    await videos_collection.update_one(
        {"video_id": video_id},
        {
            "$set": {
                "article_status": "generated",
                "article_s3_key": key,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    doc = await _get_video_or_404(video_id)
    doc.pop("_id", None)
    return Video(**doc)


@router.get("/videos/{video_id}/article", response_model=TextResponse)
async def get_video_article(video_id: str) -> TextResponse:
    doc = await _get_video_or_404(video_id)
    if doc["article_status"] != "generated" or not doc.get("article_s3_key"):
        raise HTTPException(status_code=400, detail="Article not generated yet")
    text = storage_service.get_text(doc["article_s3_key"])
    return TextResponse(text=text)
