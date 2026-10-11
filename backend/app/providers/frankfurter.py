"""Frankfurter adapter for free daily reference rates and its currency catalogue."""
from __future__ import annotations

import asyncio
import re
import time
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v2"
FRANKFURTER_RATES_URL = f"{FRANKFURTER_BASE_URL}/rates"
FRANKFURTER_CURRENCIES_URL = f"{FRANKFURTER_BASE_URL}/currencies"
DEFAULT_BASE = "EUR"
DEFAULT_QUOTES = ("USD", "RUB", "GBP", "CNY", "CHF", "JPY", "KZT", "TRY")
CACHE_TTL_SECONDS = 900
CURRENCY_CACHE_TTL_SECONDS = 86400
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class FrankfurterDataError(RuntimeError):
    """Raised when Frankfurter rates or currency metadata cannot be retrieved."""


class FrankfurterCurrencyPairUnavailable(FrankfurterDataError):
    """Raised when a requested currency pair has no published reference rate."""


def _normalize_code(value: str) -> str:
    code = value.strip().upper()
    if not _CURRENCY_RE.fullmatch(code):
        raise ValueError(f"Invalid ISO currency code: {value!r}")
    return code


def parse_rates(payload: Any, base: str, quotes: list[str] | None) -> dict[str, Any]:
    """Normalize v2 rates; quotes=None means all quotes returned by the provider."""
    if not isinstance(payload, list):
        raise FrankfurterDataError("Frankfurter returned an unexpected rates response")

    requested = set(quotes) if quotes is not None else None
    items: list[dict[str, str]] = []
    dates: list[str] = []
    seen: set[str] = set()

    for row in payload:
        if not isinstance(row, dict):
            continue
        row_base = str(row.get("base", "")).upper()
        quote = str(row.get("quote", "")).upper()
        raw_date = row.get("date")
        try:
            parsed_date = date.fromisoformat(str(raw_date))
            value = Decimal(str(row.get("rate")))
        except (ValueError, InvalidOperation):
            continue
        if row_base != base or quote == base or not _CURRENCY_RE.fullmatch(quote):
            continue
        if requested is not None and quote not in requested:
            continue
        if not value.is_finite() or value <= 0:
            continue
        rate_date = parsed_date.isoformat()
        dates.append(rate_date)
        seen.add(quote)
        items.append({
            "symbol": f"{base}/{quote}",
            "base": base,
            "quote": quote,
            "rate": format(value, "f"),
            "source": "Frankfurter",
            "rate_type": "daily_reference",
            "rate_date": rate_date,
        })

    items.sort(key=lambda item: item["quote"])
    rate_date = max(dates) if dates else None
    missing = sorted((requested or set()) - seen - ({base} if requested and base in requested else set()))
    return {
        "source": "Frankfurter",
        "source_description": "Daily reference rates sourced from central banks and official institutions",
        "rate_type": "daily_reference",
        "base": base,
        "rate_date": rate_date,
        "items": items,
        "unsupported_quotes": missing,
        "stale": False,
    }


def parse_currencies(payload: Any) -> list[dict[str, str | None]]:
    """Validate and normalize current Frankfurter currency coverage metadata."""
    if not isinstance(payload, list):
        raise FrankfurterDataError("Frankfurter returned an unexpected currencies response")
    items: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for row in payload:
        if not isinstance(row, dict):
            continue
        code = str(row.get("iso_code", "")).strip().upper()
        name = str(row.get("name", "")).strip()
        if not _CURRENCY_RE.fullmatch(code) or not name or code in seen:
            continue
        seen.add(code)
        items.append({
            "code": code,
            "name": name,
            "symbol": str(row.get("symbol") or code),
            "numeric_code": str(row.get("iso_numeric") or "") or None,
            "start_date": str(row.get("start_date") or "") or None,
            "end_date": str(row.get("end_date") or "") or None,
        })
    if not items:
        raise FrankfurterDataError("Frankfurter returned no usable currencies")
    return sorted(items, key=lambda item: str(item["code"]))


class FrankfurterProvider:
    """Small in-memory caches prevent each UI action from triggering a network call."""

    def __init__(self, url: str = FRANKFURTER_RATES_URL, cache_ttl: int = CACHE_TTL_SECONDS):
        self.url = url
        self.cache_ttl = cache_ttl
        self._cache: dict[tuple[str, tuple[str, ...] | None], tuple[float, dict[str, Any]]] = {}
        self._currency_cache: tuple[float, list[dict[str, str | None]]] | None = None
        self._rates_lock = asyncio.Lock()
        self._currency_lock = asyncio.Lock()

    async def currencies(self) -> dict[str, Any]:
        async with self._currency_lock:
            now = time.monotonic()
            if self._currency_cache and now - self._currency_cache[0] < CURRENCY_CACHE_TTL_SECONDS:
                items = self._currency_cache[1]
                return {"source": "Frankfurter", "count": len(items), "items": items, "cached": True}
            try:
                async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                    response = await client.get(FRANKFURTER_CURRENCIES_URL, headers={"Accept": "application/json"})
                    response.raise_for_status()
                    items = parse_currencies(response.json())
                self._currency_cache = (time.monotonic(), items)
                return {"source": "Frankfurter", "count": len(items), "items": items, "cached": False}
            except (httpx.HTTPError, ValueError, FrankfurterDataError) as exc:
                if self._currency_cache:
                    items = self._currency_cache[1]
                    return {"source": "Frankfurter", "count": len(items), "items": items, "cached": True, "stale": True,
                            "warning": "Frankfurter is unavailable; showing previously fetched currency metadata."}
                if isinstance(exc, FrankfurterDataError):
                    raise
                raise FrankfurterDataError(f"Frankfurter currency catalogue unavailable: {type(exc).__name__}") from exc

    async def daily_rates(self, base: str = DEFAULT_BASE, quotes: list[str] | None = None) -> dict[str, Any]:
        base_code = _normalize_code(base)
        normalized_quotes: list[str] | None
        if quotes is None:
            normalized_quotes = None
        else:
            normalized_quotes = sorted({_normalize_code(item) for item in quotes if item.strip()})
            normalized_quotes = [item for item in normalized_quotes if item != base_code]
            if not normalized_quotes:
                raise ValueError("Provide at least one quote currency different from the base currency")
            if len(normalized_quotes) > 250:
                raise ValueError("No more than 250 quote currencies can be requested at once")

        cache_key = (base_code, tuple(normalized_quotes) if normalized_quotes is not None else None)
        async with self._rates_lock:
            now = time.monotonic()
            cached = self._cache.get(cache_key)
            if cached and now - cached[0] < self.cache_ttl:
                return dict(cached[1])
            try:
                params: dict[str, str] = {"base": base_code}
                if normalized_quotes is not None:
                    params["quotes"] = ",".join(normalized_quotes)
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    response = await client.get(self.url, params=params, headers={"Accept": "application/json"})
                    response.raise_for_status()
                    payload = response.json()
                result = parse_rates(payload, base_code, normalized_quotes)
                if not result["items"]:
                    if normalized_quotes is not None:
                        raise FrankfurterCurrencyPairUnavailable(
                            f"No published reference rate for {base_code}/{','.join(normalized_quotes)}"
                        )
                    raise FrankfurterDataError("Frankfurter returned no rates for the requested currency pair(s)")
                self._cache[cache_key] = (time.monotonic(), result)
                return result
            except (httpx.HTTPError, ValueError, FrankfurterDataError) as exc:
                if cached:
                    stale_result = dict(cached[1])
                    stale_result["stale"] = True
                    stale_result["warning"] = "Frankfurter is unavailable; showing previously fetched reference rates."
                    return stale_result
                if isinstance(exc, FrankfurterDataError):
                    raise
                raise FrankfurterDataError(f"Frankfurter reference rates unavailable: {type(exc).__name__}") from exc


    async def convert(self, amount: Decimal | str | int | float, source: str, target: str) -> dict[str, Any]:
        """Convert an amount using daily reference rates (not live trading quotes)."""
        try:
            value = Decimal(str(amount))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Amount must be a valid positive number") from exc
        if not value.is_finite() or value <= 0:
            raise ValueError("Amount must be a valid positive number")

        source_code = _normalize_code(source)
        target_code = _normalize_code(target)
        if source_code == target_code:
            rate = Decimal("1")
            converted = value
            rate_date = None
            stale = False
            warning = None
        else:
            response = await self.daily_rates(source_code, [target_code])
            item = next((row for row in response["items"] if row["quote"] == target_code), None)
            if item is None:
                raise FrankfurterCurrencyPairUnavailable(f"No published reference rate for {source_code}/{target_code}")
            rate = Decimal(item["rate"])
            converted = value * rate
            rate_date = response["rate_date"]
            stale = bool(response.get("stale"))
            warning = response.get("warning")

        return {
            "source": "Frankfurter",
            "rate_type": "daily_reference",
            "rate_date": rate_date,
            "from_currency": source_code,
            "to_currency": target_code,
            "amount": format(value, "f"),
            "rate": format(rate, "f"),
            "converted_amount": format(converted, "f"),
            "stale": stale,
            "warning": warning,
        }
