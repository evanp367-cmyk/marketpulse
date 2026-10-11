"""Small RSS aggregator with bounded requests and publisher-linked headlines.

Verify each feed's terms before commercial use. This module does not reproduce
full articles or claim that headlines are investment recommendations.
"""
from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any

import httpx

FEEDS = (
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
)
REQUEST_TIMEOUT_SECONDS = 8.0
MAX_HEADLINES = 50


def _clean_text(value: str) -> str:
    """Convert common RSS HTML fragments into safe, readable plain text."""
    without_tags = re.sub(r"<[^>]*>", " ", value)
    return " ".join(unescape(without_tags).split())


def _parse_published(value: str) -> tuple[str | None, float]:
    if not value:
        return None, 0.0
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        parsed = parsed.astimezone(timezone.utc)
        return parsed.isoformat(), parsed.timestamp()
    except (TypeError, ValueError, OverflowError):
        # Keep the original provider string visible, but sort unknown dates last.
        return value, 0.0


def parse_rss_feed(publisher: str, content: str | bytes) -> list[dict[str, Any]]:
    """Parse RSS items into normalized records without returning raw HTML."""
    root = ET.fromstring(content)
    parsed_items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        title = _clean_text(item.findtext("title") or "")
        link = (item.findtext("link") or "").strip()
        published_raw = (item.findtext("pubDate") or "").strip()
        description = _clean_text(item.findtext("description") or "")
        if not title or not link or not link.startswith(("https://", "http://")):
            continue
        published_at, published_sort = _parse_published(published_raw)
        parsed_items.append({
            "title": title,
            "url": link,
            "publisher": publisher,
            "published_at": published_at,
            "summary": description[:320],
            "_published_sort": published_sort,
        })
    return parsed_items


async def _fetch_feed(
    client: httpx.AsyncClient,
    publisher: str,
    url: str,
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        response = await client.get(url)
        response.raise_for_status()
        return parse_rss_feed(publisher, response.content), None
    except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
        return [], f"{publisher}: {type(exc).__name__}"


async def latest_news(limit: int = 20) -> dict[str, Any]:
    """Fetch feed headlines concurrently, deduplicate and sort newest first."""
    bounded_limit = max(1, min(int(limit), MAX_HEADLINES))
    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT_SECONDS,
        follow_redirects=True,
        headers={"User-Agent": "MarketPulse/0.4 (+market news reader)"},
    ) as client:
        results = await asyncio.gather(
            *(_fetch_feed(client, publisher, url) for publisher, url in FEEDS)
        )

    all_items: list[dict[str, Any]] = []
    warnings: list[str] = []
    for items, warning in results:
        all_items.extend(items)
        if warning:
            warnings.append(warning)

    # If a publisher syndicates the same URL, keep one record and newest date order.
    unique = {item["url"]: item for item in all_items}
    merged = sorted(unique.values(), key=lambda item: item["_published_sort"], reverse=True)
    items = []
    for item in merged[:bounded_limit]:
        item.pop("_published_sort", None)
        items.append(item)

    return {
        "items": items,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sources": [name for name, _ in FEEDS],
        "warnings": warnings,
        "disclaimer": "Headlines are provided by third-party publishers. Verify source terms before commercial redistribution; this is not investment advice.",
    }
