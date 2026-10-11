"""Bank of Russia daily official exchange-rate adapter.

These are official reference rates, not executable/realtime FX quotes.
"""
from __future__ import annotations

import asyncio
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

CBR_DAILY_URL = "https://www.cbr.ru/scripts/XML_daily.asp"
CACHE_TTL_SECONDS = 300


class CBRDataError(RuntimeError):
    """Raised when Bank of Russia data cannot be retrieved or parsed."""


def _decimal_text(value: str) -> Decimal:
    return Decimal(value.strip().replace(" ", "").replace(",", "."))


def parse_daily_xml(xml_text: str | bytes) -> dict[str, Any]:
    """Parse the official XML_daily.asp response into normalized RUB quotes."""
    try:
        root = ET.fromstring(xml_text)
        raw_date = root.attrib.get("Date", "")
        rate_date = datetime.strptime(raw_date, "%d.%m.%Y").date().isoformat()
    except (ET.ParseError, ValueError) as exc:
        raise CBRDataError("Bank of Russia returned an invalid daily-rate document") from exc

    items: list[dict[str, str]] = []
    for node in root.findall("Valute"):
        code = (node.findtext("CharCode") or "").strip().upper()
        if not code:
            continue
        try:
            nominal = _decimal_text(node.findtext("Nominal") or "1")
            value = _decimal_text(node.findtext("Value") or "")
            if nominal <= 0:
                continue
            rate = value / nominal
        except (InvalidOperation, ZeroDivisionError):
            continue

        items.append({
            "symbol": f"{code}/RUB",
            "base": code,
            "quote": "RUB",
            "name": (node.findtext("Name") or code).strip(),
            "nominal": str(nominal),
            "official_value": str(value),
            "rate": format(rate, "f"),
            "source": "Bank of Russia",
            "rate_type": "official_daily_reference",
            "rate_date": rate_date,
        })

    if not items:
        raise CBRDataError("Bank of Russia daily-rate response contained no currencies")
    return {"source": "Bank of Russia", "rate_type": "official_daily_reference", "rate_date": rate_date, "items": items}


def filter_daily_rates(all_rates: dict[str, Any], symbols: list[str] | None = None) -> dict[str, Any]:
    """Return every published CBR currency by default, or filter explicit symbols."""
    requested = {item.strip().upper() for item in symbols if item.strip()} if symbols is not None else None
    if requested is None:
        filtered = list(all_rates["items"])
        missing: list[str] = []
    else:
        filtered = [item for item in all_rates["items"] if item["base"] in requested]
        missing = sorted(requested - {item["base"] for item in filtered})
    result = {key: value for key, value in all_rates.items() if key != "items"}
    result["items"] = filtered
    if missing:
        result["unsupported_symbols"] = missing
    result.setdefault("stale", False)
    return result


class CBRDailyProvider:
    """Fetch and briefly cache daily rates to avoid repeated upstream requests."""

    def __init__(self, url: str = CBR_DAILY_URL, cache_ttl: int = CACHE_TTL_SECONDS):
        self.url = url
        self.cache_ttl = cache_ttl
        self._cached: dict[str, Any] | None = None
        self._cached_at = 0.0
        self._lock = asyncio.Lock()

    async def daily_rates(self, symbols: list[str] | None = None) -> dict[str, Any]:
        async with self._lock:
            now = time.monotonic()
            if self._cached is not None and now - self._cached_at < self.cache_ttl:
                all_rates = self._cached
            else:
                try:
                    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                        response = await client.get(self.url, headers={"Accept": "application/xml,text/xml"})
                        response.raise_for_status()
                    all_rates = parse_daily_xml(response.content)
                    self._cached = all_rates
                    self._cached_at = time.monotonic()
                except (httpx.HTTPError, CBRDataError) as exc:
                    if self._cached is None:
                        if isinstance(exc, CBRDataError):
                            raise
                        raise CBRDataError(f"Bank of Russia rates unavailable: {type(exc).__name__}") from exc
                    # Explicitly flag the fallback rather than pretending stale cached data is fresh.
                    all_rates = {**self._cached, "stale": True, "warning": "Upstream unavailable; showing previously fetched official rates."}

        return filter_daily_rates(all_rates, symbols)
