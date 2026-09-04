from fastapi import APIRouter, HTTPException

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
    digest = await digest_svc.refresh_digest()
    if not digest.get("text"):
        raise HTTPException(status_code=503, detail="No recent articles are available for a digest")
    return digest
