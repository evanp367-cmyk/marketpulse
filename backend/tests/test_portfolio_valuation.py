from decimal import Decimal

from backend.app.portfolio.valuation import build_portfolio_response, quote_asset_for_symbol, value_position


def test_quote_asset_parses_longest_known_quote_suffix():
    assert quote_asset_for_symbol("btcusdt") == "USDT"
    assert quote_asset_for_symbol("ETHBTC") == "BTC"
    assert quote_asset_for_symbol("SOLFDUSD") == "FDUSD"
    assert quote_asset_for_symbol("UNKNOWNPAIR") == "UNKNOWN"


def test_position_has_market_value_cost_basis_and_unrealized_pnl():
    result = value_position(
        {"id": 1, "symbol": "BTCUSDT", "quantity": "0.25", "average_entry_price": "60000"},
        {"BTCUSDT": "65000"},
    )
    assert result["market_value"] == "16250.00"
    assert result["cost_basis"] == "15000.00"
    assert result["unrealized_pnl"] == "1250.00"
    assert result["unrealized_pnl_percent"] == "8.333333333333333333333333333"
    assert result["valuation_status"] == "available"
    assert result["quote_asset"] == "USDT"


def test_position_without_entry_price_has_no_fake_pnl():
    result = value_position(
        {"id": 2, "symbol": "ETHUSDT", "quantity": "2", "average_entry_price": None},
        {"ETHUSDT": "3000"},
    )
    assert result["market_value"] == "6000"
    assert result["cost_basis"] is None
    assert result["unrealized_pnl"] is None
    assert result["unrealized_pnl_percent"] is None


def test_missing_quote_keeps_position_but_marks_valuation_unavailable():
    result = value_position(
        {"id": 3, "symbol": "SOMEUSDT", "quantity": "5", "average_entry_price": "2"},
        {},
    )
    assert result["market_value"] is None
    assert result["valuation_status"] == "unavailable"
    assert result["unrealized_pnl"] is None


def test_portfolio_totals_are_grouped_by_quote_asset_not_mixed():
    positions = [
        {"id": 1, "symbol": "BTCUSDT", "quantity": "1", "average_entry_price": "100"},
        {"id": 2, "symbol": "ETHBTC", "quantity": "2", "average_entry_price": "0.05"},
    ]
    response = build_portfolio_response(positions, {"BTCUSDT": "110", "ETHBTC": "0.06"}, "2026-10-11T12:00:00+00:00")
    totals = {row["quote_asset"]: row for row in response["totals_by_quote_asset"]}
    assert totals["USDT"]["market_value"] == "110"
    assert totals["USDT"]["unrealized_pnl"] == "10"
    assert totals["BTC"]["market_value"] == "0.12"
    assert totals["BTC"]["unrealized_pnl"] == "0.02"
    assert len(totals) == 2


def test_no_float_arithmetic_in_summary():
    response = build_portfolio_response(
        [{"id": 1, "symbol": "BTCUSDT", "quantity": Decimal("0.1"), "average_entry_price": Decimal("3")}],
        {"BTCUSDT": "4"},
        None,
    )
    assert response["items"][0]["market_value"] == "0.4"
    assert response["items"][0]["unrealized_pnl"] == "0.1"


def test_missing_prices_do_not_turn_total_value_into_zero():
    response = build_portfolio_response(
        [{"id": 1, "symbol": "BTCUSDT", "quantity": "0.1", "average_entry_price": "50000"}],
        {}, None,
    )
    total = response["totals_by_quote_asset"][0]
    assert total["market_value"] is None
    assert total["unrealized_pnl"] is None
    assert total["cost_basis"] == "5000.0"
    assert total["unpriced_positions"] == 1


def test_partial_valuation_preserves_known_value_and_missing_count():
    response = build_portfolio_response(
        [
            {"id": 1, "symbol": "BTCUSDT", "quantity": "0.1", "average_entry_price": "50000"},
            {"id": 2, "symbol": "ETHUSDT", "quantity": "1", "average_entry_price": "2000"},
        ],
        {"BTCUSDT": "60000"}, None,
    )
    total = response["totals_by_quote_asset"][0]
    assert total["market_value"] == "6000.0"
    assert total["priced_positions"] == total["unpriced_positions"] == 1


import json
import pytest
from backend.app.providers.binance import BinancePublicProvider


@pytest.mark.asyncio
async def test_ticker_prices_normalizes_and_deduplicates_symbols(monkeypatch):
    provider = BinancePublicProvider()
    captured = {}

    async def fake_get(path, params=None):
        captured["path"] = path
        captured["params"] = params
        return [
            {"symbol": "BTCUSDT", "price": "65000.1200"},
            {"symbol": "ETHUSDT", "price": "3000.50"},
        ]

    monkeypatch.setattr(provider, "_get", fake_get)
    result = await provider.ticker_prices(["btcusdt", "BTCUSDT", " ETHUSDT "])
    assert captured["path"] == "/api/v3/ticker/price"
    assert json.loads(captured["params"]["symbols"]) == ["BTCUSDT", "ETHUSDT"]
    assert result == {"BTCUSDT": "65000.1200", "ETHUSDT": "3000.50"}


@pytest.mark.asyncio
async def test_ticker_24h_symbol_filter_is_case_insensitive(monkeypatch):
    provider = BinancePublicProvider()

    async def fake_get(path, params=None):
        return [
            {"symbol": "BTCUSDT", "lastPrice": "65000", "priceChangePercent": "1.2", "quoteVolume": "100"},
            {"symbol": "ETHUSDT", "lastPrice": "3000", "priceChangePercent": "-0.5", "quoteVolume": "200"},
        ]

    monkeypatch.setattr(provider, "_get", fake_get)
    result = await provider.ticker_24h(["btcusdt"])
    assert [item["symbol"] for item in result] == ["BTCUSDT"]


@pytest.mark.asyncio
async def test_ticker_24h_empty_filter_does_not_return_entire_market(monkeypatch):
    provider = BinancePublicProvider()

    async def fake_get(path, params=None):
        return [{"symbol": "BTCUSDT", "lastPrice": "65000", "priceChangePercent": "1.2", "quoteVolume": "100"}]

    monkeypatch.setattr(provider, "_get", fake_get)
    assert await provider.ticker_24h([""]) == []


@pytest.mark.asyncio
async def test_klines_preserves_exact_close_time_and_closed_flag(monkeypatch):
    provider = BinancePublicProvider()
    async def fake_get(path, params=None):
        return [[1_700_000_000_000, "1", "2", "0.5", "1.5", "10", 1_700_000_003_999]]
    monkeypatch.setattr(provider, "_get", fake_get)
    result = await provider.klines("BTCUSDT", "1m", 1)
    assert result[0]["close_time"] == 1_700_000_003_999
    assert result[0]["time"] == 1_700_000_000
    assert result[0]["closed"] is True
