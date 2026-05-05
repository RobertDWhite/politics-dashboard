"""Per-article summary worker. Pulls from a queue, calls the LLM, caches results."""
from __future__ import annotations

import asyncio
import logging

from app.llm import llm

logger = logging.getLogger(__name__)

_summaries: dict[str, str] = {}
_queue: asyncio.Queue = asyncio.Queue()
_queued_ids: set[str] = set()

_SYSTEM = (
    "You are a news summarizer. Output only the summary — 2-3 sentences, "
    "concise and factual. No preamble, no labels, no explanation."
)


def enqueue(article_id: str, title: str, content: str) -> None:
    if article_id not in _summaries and article_id not in _queued_ids:
        _queued_ids.add(article_id)
        _queue.put_nowait((article_id, title, content))


def get_summary(article_id: str) -> str | None:
    return _summaries.get(article_id)


async def summarizer_worker() -> None:
    while True:
        article_id, title, content = await _queue.get()
        try:
            text = await llm.chat(
                _SYSTEM,
                f"Title: {title}\n\n{content}",
                max_tokens=200,
            )
            _summaries[article_id] = text
        except Exception as e:
            logger.warning("Summarization failed for %s: %s", article_id, e)
        finally:
            _queued_ids.discard(article_id)
            _queue.task_done()
