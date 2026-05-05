"""24-hour digest of recent articles, regenerated periodically."""
from __future__ import annotations

import asyncio
import logging
import time

from app.config import config
from app.llm import llm
from app.store import articles as _articles
from app.store import store_lock as _store_lock

logger = logging.getLogger(__name__)

_digest: dict = {}
_digest_lock = asyncio.Lock()

_SYSTEM = (
    "You are a political news analyst writing a structured 24-hour digest "
    "for a markdown-rendered dashboard.\n\n"
    "FORMAT (strict):\n"
    "Group stories into 3-6 thematic sections. Pick category names that fit "
    "the actual news (examples: Executive Branch, Congress, Courts & Legal, "
    "Foreign Policy, Investigations, Elections, Economy, Culture & Media). "
    "Skip categories with nothing to report.\n\n"
    "For each section use this exact pattern:\n"
    "## Category Name\n"
    "- **Headline phrase** — 1-2 sentence factual summary with key actors and outcome.\n"
    "- **Headline phrase** — summary.\n\n"
    "End with a final section:\n"
    "## Bottom Line\n"
    "1-2 sentences identifying the day's dominant narrative.\n\n"
    "RULES:\n"
    "- Bold the lead phrase of each bullet with **double asterisks**.\n"
    "- Use an em dash (—) between the bold lead and the summary.\n"
    "- Be factual, neutral, specific. Name people, agencies, and numbers.\n"
    "- No preamble, no 'Here is...', no closing remarks. Start with the first ## header."
)


async def refresh_digest() -> None:
    cutoff = time.time() - 86400
    async with _store_lock:
        recent = [a for a in _articles if a["published"] >= cutoff]

    if not recent:
        return

    articles_text = "\n\n".join(
        f"[{a['source']}] {a['title']}: {a['content'][:600]}"
        for a in recent[:60]
    )

    try:
        text = await llm.chat(_SYSTEM, articles_text, max_tokens=1200)
        async with _digest_lock:
            _digest.update({"text": text, "updated_at": time.time(), "article_count": len(recent)})
        logger.info("Digest refreshed from %d articles", len(recent))
    except Exception as e:
        logger.warning("Digest generation failed: %s", e)


def get_digest() -> dict:
    return dict(_digest)


async def digest_loop() -> None:
    while True:
        await refresh_digest()
        await asyncio.sleep(config.refresh.digest_seconds)
