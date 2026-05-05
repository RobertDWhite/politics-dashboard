from fastapi import APIRouter, Query

from app.services import summarizer
from app.store import get_articles

router = APIRouter(prefix="/articles")


@router.get("")
async def list_articles(
    category: str | None = Query(None),
    limit: int = Query(50, le=150),
    offset: int = Query(0),
):
    items = await get_articles(category=category, limit=limit, offset=offset)
    return [{**item, "summary": summarizer.get_summary(item["id"])} for item in items]
