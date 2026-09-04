"""24-hour digest of recent articles, regenerated periodically."""
from __future__ import annotations

import asyncio
import logging
import re
import time

from app.config import config
from app.llm import llm
from app.store import articles as _articles
from app.store import store_lock as _store_lock

logger = logging.getLogger(__name__)

_digest: dict = {}
_digest_lock = asyncio.Lock()
_refresh_lock = asyncio.Lock()

_CITATION = re.compile(r"\[S(\d+)\]")
_PRESIDENT_REFERENCE = re.compile(
    r"\bPresident\s+([A-Z][A-Za-z'’-]*(?:\s+[A-Z][A-Za-z'’-]*){0,2})"
)

_SYSTEM = (
    "You are a political news analyst writing a structured 24-hour digest "
    "for a markdown-rendered dashboard. The supplied source excerpts are the "
    "only authority: do not use background knowledge, fill gaps, or infer facts "
    "not directly supported by them.\n\n"
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
    "- Be factual, neutral, and specific. Name people, agencies, and numbers only "
    "when the supplied source excerpts do.\n"
    "- Every bullet must end with one or more source citations in the form [S1] "
    "or [S1][S2]. Cite only the source IDs supplied in the input.\n"
    "- If a detail is not directly supported by a source, omit it.\n"
    "- No preamble, no 'Here is...', no closing remarks. Start with the first ## header."
)


def _source_material(articles: list[dict]) -> str:
    """Build a bounded, numbered evidence set for the model and reader."""
    parts = []
    for number, article in enumerate(articles, start=1):
        published = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(article["published"]))
        parts.append(
            f"[S{number}]\n"
            f"Source: {article['source']}\n"
            f"Published: {published}\n"
            f"Title: {article['title']}\n"
            f"URL: {article['url']}\n"
            f"Excerpt: {article['content'][:800]}"
        )
    return "\n\n".join(parts)


def _source_appendix(articles: list[dict]) -> str:
    lines = ["## Sources"]
    lines.extend(
        f"[S{number}] {article['source']} — {article['url']}"
        for number, article in enumerate(articles, start=1)
    )
    return "\n".join(lines)


def _validate_digest(text: str, articles: list[dict]) -> None:
    """Reject ungrounded or templated model output before it can be published."""
    if not text or len(text.strip()) < 120:
        raise ValueError("digest is empty or implausibly short")
    lowered = text.casefold()
    if "headline phrase" in lowered or "1-2 sentence factual summary" in lowered:
        raise ValueError("digest repeats the prompt template")

    bullets = [line for line in text.splitlines() if line.lstrip().startswith("-")]
    if len(bullets) < 2:
        raise ValueError("digest has too few sourced bullets")

    for bullet in bullets:
        citations = [int(match) for match in _CITATION.findall(bullet)]
        if not citations:
            raise ValueError("digest bullet has no source citation")
        if any(number < 1 or number > len(articles) for number in citations):
            raise ValueError("digest cites a source outside the supplied evidence")

    source_corpus = " ".join(
        f"{article['title']} {article['content']}" for article in articles
    ).casefold()
    for match in _PRESIDENT_REFERENCE.finditer(text):
        phrase = match.group(0).casefold()
        if phrase not in source_corpus:
            raise ValueError(f"unsupported presidential reference: {match.group(0)}")


def _safe_fallback(articles: list[dict]) -> str:
    """A source-only fallback is preferable to an unsourced invented digest."""
    lines = [
        "## Source-backed updates",
        "The AI digest did not pass grounding checks. Review these current source headlines instead:",
    ]
    for number, article in enumerate(articles[:12], start=1):
        lines.append(f"- **{article['title']}** — Reported by {article['source']}. [S{number}]")
    lines.extend([
        "",
        "## Bottom Line",
        "No AI synthesis was published because it could not be validated against the supplied sources.",
    ])
    return "\n".join(lines)


async def refresh_digest() -> dict:
    """Generate and return a fresh, source-grounded digest exactly once per caller."""
    async with _refresh_lock:
        cutoff = time.time() - 86400
        async with _store_lock:
            recent = [a for a in _articles if a["published"] >= cutoff]

        recent.sort(key=lambda article: article["published"], reverse=True)
        evidence = recent[:40]
        if not evidence:
            logger.warning("Digest refresh skipped: no articles in the last 24 hours")
            return get_digest()

        try:
            candidate = await llm.chat(_SYSTEM, _source_material(evidence), max_tokens=1200)
            _validate_digest(candidate, evidence)
            text = candidate
        except Exception as e:
            logger.warning("Digest rejected by grounding checks: %s", e)
            text = _safe_fallback(evidence)

        text = f"{text}\n\n{_source_appendix(evidence)}"
        async with _digest_lock:
            _digest.update({"text": text, "updated_at": time.time(), "article_count": len(recent)})
            refreshed = dict(_digest)
        logger.info("Digest refreshed from %d articles", len(recent))
        return refreshed


def get_digest() -> dict:
    return dict(_digest)


async def digest_loop() -> None:
    while True:
        await refresh_digest()
        await asyncio.sleep(config.refresh.digest_seconds)
