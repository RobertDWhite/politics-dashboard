"""In-memory article store shared across services."""
from __future__ import annotations

import asyncio

articles: list[dict] = []
seen_ids: set[str] = set()
store_lock = asyncio.Lock()


async def get_articles(category: str | None, limit: int, offset: int) -> list[dict]:
    async with store_lock:
        items = list(articles)
    if category:
        items = [a for a in items if a["category"] == category]
    return items[offset : offset + limit]
