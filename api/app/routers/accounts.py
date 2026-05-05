import asyncio

from fastapi import APIRouter

from app.config import config
from app.services import digest as digest_svc
from app.services import twitter

router = APIRouter(prefix="/accounts")


@router.get("")
async def get_accounts():
    return {key: cat.handles for key, cat in config.twitter.categories.items()}


@router.get("/summaries")
async def get_summaries():
    summaries = twitter.get_summaries()
    return {
        key: {h: summaries.get(h, {"summary": None, "updated_at": None}) for h in cat.handles}
        for key, cat in config.twitter.categories.items()
    }


@router.get("/digest")
async def get_digest():
    return digest_svc.get_digest()


@router.post("/digest/refresh")
async def trigger_digest_refresh():
    asyncio.create_task(digest_svc.refresh_digest())
    return {"status": "refresh triggered"}
