"""
Article ingestion. Two sources are supported:

- "rss": pull each category's RSS/Atom URLs directly. No external service.
- "freshrss": pull from a FreshRSS instance via the Greader API, using
  per-category labels. Useful when feeds are already curated in FreshRSS.

Both produce the same article dict shape and store into app.store.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import httpx

from app.config import config
from app.store import articles as _articles
from app.store import seen_ids as _seen_ids
from app.store import store_lock as _store_lock
from app.services.summarizer import enqueue

logger = logging.getLogger(__name__)


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "").strip()


def _hash_id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


# ── RSS direct ──────────────────────────────────────────────────────────────


def _parse_rss_pubdate(s: str) -> int:
    if not s:
        return 0
    try:
        return int(parsedate_to_datetime(s).timestamp())
    except (TypeError, ValueError):
        return 0


def _parse_atom_date(s: str) -> int:
    if not s:
        return 0
    try:
        from datetime import datetime
        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return 0


async def _fetch_rss_feed(url: str, category_key: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=30.0, follow_redirects=True,
                                headers={"User-Agent": "politics-dashboard/1.0"})
        resp.raise_for_status()

    items: list[dict] = []
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        logger.warning("Bad feed at %s: %s", url, e)
        return items

    # RSS 2.0
    channel = root.find("channel")
    source = (channel.findtext("title") if channel is not None else "") or url
    for item in root.findall(".//channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = _parse_rss_pubdate(item.findtext("pubDate") or "")
        desc = item.findtext("description") or ""
        content_el = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
        body = content_el.text if content_el is not None and content_el.text else desc
        items.append(_make_article(link or title, title, link, pub, source, body, category_key))

    # Atom
    if not items:
        ns = "{http://www.w3.org/2005/Atom}"
        source = root.findtext(f"{ns}title") or url
        for entry in root.findall(f"{ns}entry"):
            title = (entry.findtext(f"{ns}title") or "").strip()
            link_el = entry.find(f"{ns}link")
            link = link_el.attrib.get("href", "") if link_el is not None else ""
            pub = _parse_atom_date(
                entry.findtext(f"{ns}published") or entry.findtext(f"{ns}updated") or ""
            )
            body = entry.findtext(f"{ns}content") or entry.findtext(f"{ns}summary") or ""
            items.append(_make_article(link or title, title, link, pub, source, body, category_key))

    return items


def _make_article(uid_seed: str, title: str, url: str, pub: int,
                  source: str, body: str, category: str) -> dict:
    return {
        "id": _hash_id(category, uid_seed),
        "title": title,
        "url": url,
        "published": pub or int(time.time()),
        "source": source,
        "content": _strip_html(body)[:3000],
        "category": category,
    }


async def _refresh_rss() -> list[dict]:
    fetched: list[dict] = []
    for cat_key, cat in config.feeds.categories.items():
        for url in cat.urls:
            try:
                items = await _fetch_rss_feed(url, cat_key)
                fetched.extend(items[: config.feeds.max_per_category])
            except Exception as e:
                logger.warning("Feed %s failed: %s", url, e)
    return fetched


# ── FreshRSS Greader ───────────────────────────────────────────────────────


_freshrss_token: str | None = None
_freshrss_token_lock = asyncio.Lock()


async def _freshrss_login() -> str:
    fr = config.feeds.freshrss
    if not fr:
        raise RuntimeError("freshrss config missing")
    password = os.environ.get(fr.password_env, "")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{fr.url}/accounts/ClientLogin",
            data={"Email": fr.username, "Passwd": password},
            timeout=15.0,
        )
        resp.raise_for_status()
    for line in resp.text.splitlines():
        if line.startswith("Auth="):
            return line[5:]
    raise ValueError("No Auth token in FreshRSS login response")


async def _freshrss_token_get() -> str:
    global _freshrss_token
    async with _freshrss_token_lock:
        if not _freshrss_token:
            _freshrss_token = await _freshrss_login()
        return _freshrss_token


async def _fetch_freshrss_category(label: str, category_key: str, since: int) -> list[dict]:
    global _freshrss_token
    fr = config.feeds.freshrss
    if not fr:
        return []
    url = (
        f"{fr.url}/reader/api/0/stream/contents/user/-/label/{label}"
        f"?n={config.feeds.max_per_category}&ot={since}&output=json"
    )

    for _ in range(2):
        token = await _freshrss_token_get()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"GoogleLogin auth={token}"},
                timeout=30.0,
            )
        if resp.status_code != 401:
            break
        async with _freshrss_token_lock:
            if _freshrss_token == token:
                _freshrss_token = None

    resp.raise_for_status()

    items = []
    for raw in resp.json().get("items", []):
        if raw.get("published", 0) < since:
            continue
        article_id = raw.get("id", "")
        if not article_id:
            continue
        url_val = (raw.get("canonical") or [{}])[0].get("href", "")
        items.append({
            "id": article_id,
            "title": raw.get("title", ""),
            "url": url_val,
            "published": raw.get("published", 0),
            "source": raw.get("origin", {}).get("title", ""),
            "content": _strip_html(raw.get("summary", {}).get("content", ""))[:3000],
            "category": category_key,
        })
    return items


async def _refresh_freshrss() -> list[dict]:
    since = int(time.time()) - config.feeds.lookback_hours * 3600
    fetched: list[dict] = []
    for cat_key, cat in config.feeds.categories.items():
        label = cat.freshrss_label or cat.label
        try:
            fetched.extend(await _fetch_freshrss_category(label, cat_key, since))
        except Exception as e:
            logger.warning("FreshRSS category %s failed: %s", label, e)
    return fetched


# ── Refresh + dedupe ───────────────────────────────────────────────────────


async def refresh_articles() -> None:
    if config.feeds.source == "freshrss":
        fetched = await _refresh_freshrss()
    else:
        fetched = await _refresh_rss()

    if not fetched:
        return

    since = int(time.time()) - config.feeds.lookback_hours * 3600
    by_id = {item["id"]: item for item in fetched if item["published"] >= since}

    async with _store_lock:
        existing = {a["id"]: a for a in _articles if a["published"] >= since}
        merged = {**existing, **by_id}

        for article_id, item in by_id.items():
            if article_id not in _seen_ids:
                _seen_ids.add(article_id)
                if item["title"] and item["content"]:
                    enqueue(article_id, item["title"], item["content"])

        seen_titles: set[tuple[str, str]] = set()
        deduped = []
        for article in sorted(merged.values(), key=lambda a: a["published"], reverse=True):
            key = (article["source"], article["title"])
            if key not in seen_titles:
                seen_titles.add(key)
                deduped.append(article)

        _articles.clear()
        _articles.extend(deduped)

    logger.info("Articles: %d total (%d fetched, source=%s)",
                len(_articles), len(by_id), config.feeds.source)


async def refresh_loop() -> None:
    while True:
        await asyncio.sleep(config.refresh.articles_seconds)
        try:
            await refresh_articles()
        except Exception as e:
            logger.exception("refresh_articles failed: %s", e)
