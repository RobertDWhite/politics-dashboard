"""
Per-account X/Twitter summaries via Nitter RSS.

Nitter is an external dependency: deploy your own and point NITTER_URL at it.
If twitter.enabled is false (or no nitter_url), this module no-ops and the UI
hides the X panel.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
import xml.etree.ElementTree as ET

import httpx

from app.config import config
from app.llm import llm

logger = logging.getLogger(__name__)

_summaries: dict[str, dict] = {}
_lock = asyncio.Lock()

_SYSTEM = (
    "You are a political analyst. Summarize the recent posts from this "
    "account in 3-4 sentences. Focus on main themes and positions. "
    "Output only the summary, no preamble."
)


def _all_handles() -> list[str]:
    seen: list[str] = []
    for cat in config.twitter.categories.values():
        for h in cat.handles:
            if h not in seen:
                seen.append(h)
    return seen


async def _fetch_tweets(handle: str, count: int = 20) -> list[str]:
    url = f"{config.twitter.nitter_url.rstrip('/')}/{handle}/rss"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()

    root = ET.fromstring(resp.content)
    tweets = []
    for item in root.findall(".//item")[:count]:
        title = item.findtext("title") or ""
        desc = item.findtext("description") or ""
        desc = re.sub(r"<[^>]+>", " ", desc).strip()
        text = desc if len(desc) > len(title) else title
        if text:
            tweets.append(text[:400])
    return tweets


async def _summarize_handle(handle: str) -> str:
    tweets = await _fetch_tweets(handle)
    if not tweets:
        return "No recent posts available."
    body = "\n".join(f"- {t}" for t in tweets)
    return await llm.chat(_SYSTEM, f"Recent posts from @{handle}:\n{body}", max_tokens=250)


async def refresh_all() -> None:
    if not config.twitter.enabled or not config.twitter.nitter_url:
        return
    refresh_secs = config.refresh.twitter_seconds
    handles = _all_handles()
    now = time.time()
    async with _lock:
        stale = [
            h for h in handles
            if h not in _summaries or now - _summaries[h]["updated_at"] > refresh_secs
        ]

    for handle in stale:
        try:
            summary = await _summarize_handle(handle)
            async with _lock:
                _summaries[handle] = {"summary": summary, "updated_at": time.time()}
        except Exception as e:
            logger.warning("Failed to summarize @%s: %s", handle, e)


def get_summaries() -> dict[str, dict]:
    return dict(_summaries)


async def summarizer_loop() -> None:
    while True:
        await refresh_all()
        await asyncio.sleep(config.refresh.twitter_seconds)
