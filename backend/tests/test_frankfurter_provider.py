import asyncio
import pytest

from backend.app.providers import frankfurter as module
from backend.app.providers.frankfurter import FrankfurterProvider


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeAsyncClient:
    calls = []
    rate_payload = [
        {"date": "2026-10-09", "base": "EUR", "quote": "USD", "rate": 1.15},
        {"date": "2026-10-09", "base": "EUR", "quote": "ZAR", "rate": 19.2},
    ]
    currency_payload = [
        {"iso_code": "USD", "iso_numeric": "840", "name": "US Dollar", "symbol": "$"},
        {"iso_code": "ZAR", "iso_numeric": "710", "name": "South African Rand", "symbol": "R"},
    ]

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None, headers=None):
        self.calls.append((url, params))
        if url == module.FRANKFURTER_CURRENCIES_URL:
            return FakeResponse(self.currency_payload)
        return FakeResponse(self.rate_payload)


def test_provider_fetches_all_rates_when_quotes_are_omitted_and_caches(monkeypatch):
    FakeAsyncClient.calls = []
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeAsyncClient)
    provider = FrankfurterProvider(cache_ttl=900)

    async def scenario():
        first = await provider.daily_rates("EUR")
        second = await provider.daily_rates("EUR")
        return first, second

    first, second = asyncio.run(scenario())
    assert {item["quote"] for item in first["items"]} == {"USD", "ZAR"}
    assert second["items"] == first["items"]
    assert len(FakeAsyncClient.calls) == 1
    assert FakeAsyncClient.calls[0][1] == {"base": "EUR"}


def test_provider_fetches_and_caches_currency_catalog(monkeypatch):
    FakeAsyncClient.calls = []
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeAsyncClient)
    provider = FrankfurterProvider()

    async def scenario():
        first = await provider.currencies()
        second = await provider.currencies()
        return first, second

    first, second = asyncio.run(scenario())
    assert first["count"] == 2
    assert [item["code"] for item in first["items"]] == ["USD", "ZAR"]
    assert second["cached"] is True
    assert len(FakeAsyncClient.calls) == 1


def test_provider_converts_using_daily_reference_rate(monkeypatch):
    FakeAsyncClient.calls = []
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeAsyncClient)
    provider = FrankfurterProvider(cache_ttl=900)

    result = asyncio.run(provider.convert("10.5", "eur", "usd"))

    assert result["from_currency"] == "EUR"
    assert result["to_currency"] == "USD"
    assert result["amount"] == "10.5"
    assert result["rate"] == "1.15"
    assert result["converted_amount"] == "12.075"
    assert result["rate_date"] == "2026-10-09"
    assert result["rate_type"] == "daily_reference"
    assert FakeAsyncClient.calls[0][1] == {"base": "EUR", "quotes": "USD"}


def test_provider_same_currency_conversion_does_not_need_provider(monkeypatch):
    FakeAsyncClient.calls = []
    monkeypatch.setattr(module.httpx, "AsyncClient", FakeAsyncClient)
    provider = FrankfurterProvider()

    result = asyncio.run(provider.convert("2.75", "usd", "USD"))

    assert result["rate"] == "1"
    assert result["converted_amount"] == "2.75"
    assert result["rate_date"] is None
    assert FakeAsyncClient.calls == []


def test_provider_rejects_non_positive_conversion_amount():
    provider = FrankfurterProvider()
    with pytest.raises(ValueError):
        asyncio.run(provider.convert("0", "EUR", "USD"))
