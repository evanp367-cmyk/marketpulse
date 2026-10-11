import pytest
from backend.app.providers.frankfurter import FrankfurterDataError, parse_rates, parse_currencies


def test_parse_rates_normalizes_codes_and_marks_missing_quotes():
    payload = [
        {"date": "2026-10-09", "base": "EUR", "quote": "USD", "rate": 1.1572},
        {"date": "2026-10-09", "base": "EUR", "quote": "GBP", "rate": 0.8721},
        {"date": "2026-10-09", "base": "EUR", "quote": "RUB", "rate": 90.5},
        {"date": "2026-10-09", "base": "EUR", "quote": "JPY", "rate": -1},
    ]
    result = parse_rates(payload, "EUR", ["USD", "GBP", "RUB", "JPY", "CHF"])
    assert result["source"] == "Frankfurter"
    assert result["rate_date"] == "2026-10-09"
    rates = {item["quote"]: item["rate"] for item in result["items"]}
    assert rates == {"GBP": "0.8721", "RUB": "90.5", "USD": "1.1572"}
    assert result["unsupported_quotes"] == ["CHF", "JPY"]
    assert result["rate_type"] == "daily_reference"


def test_parse_rates_rejects_wrong_payload():
    with pytest.raises(FrankfurterDataError):
        parse_rates({"rates": {}}, "EUR", ["USD"])


def test_parse_rates_skips_mismatched_base_and_quote():
    result = parse_rates(
        [{"date": "2026-10-09", "base": "USD", "quote": "EUR", "rate": 0.9}],
        "EUR",
        ["USD"],
    )
    assert result["items"] == []
    assert result["unsupported_quotes"] == ["USD"]


def test_parse_rates_without_quote_filter_accepts_all_supported_quotes():
    payload = [
        {"date": "2026-10-09", "base": "EUR", "quote": "USD", "rate": 1.15},
        {"date": "2026-10-09", "base": "EUR", "quote": "ZAR", "rate": 19.2},
        {"date": "2026-10-09", "base": "EUR", "quote": "EUR", "rate": 1},
        {"date": "2026-10-09", "base": "USD", "quote": "GBP", "rate": 0.8},
    ]
    result = parse_rates(payload, "EUR", None)
    assert {item["quote"] for item in result["items"]} == {"USD", "ZAR"}
    assert result["unsupported_quotes"] == []


def test_parse_currencies_filters_invalid_and_duplicate_entries():
    result = parse_currencies([
        {"iso_code": "USD", "name": "US Dollar", "symbol": "$", "iso_numeric": "840"},
        {"iso_code": "usd", "name": "Duplicate", "symbol": "$"},
        {"iso_code": "bad-code", "name": "Invalid", "symbol": "?"},
        {"iso_code": "EUR", "name": "Euro", "symbol": "€"},
    ])
    assert [item["code"] for item in result] == ["EUR", "USD"]
    assert next(item for item in result if item["code"] == "USD")["numeric_code"] == "840"


def test_parse_currencies_rejects_empty_or_invalid_payload():
    with pytest.raises(FrankfurterDataError):
        parse_currencies([])
    with pytest.raises(FrankfurterDataError):
        parse_currencies({"currencies": []})
