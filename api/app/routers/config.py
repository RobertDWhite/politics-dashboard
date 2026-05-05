"""Public config endpoint for the UI (titles, category labels, twitter on/off)."""
from fastapi import APIRouter

from app.config import config

router = APIRouter()


@router.get("/config")
async def get_public_config():
    return {
        "title": config.title,
        "categories": [
            {"key": key, "label": cat.label}
            for key, cat in config.feeds.categories.items()
        ],
        "twitter": {
            "enabled": config.twitter.enabled and bool(config.twitter.nitter_url),
            "categories": [
                {"key": key, "label": cat.label}
                for key, cat in config.twitter.categories.items()
            ],
        },
    }
