from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

# Longest suffixes first so quote assets such as FDUSD are not mistaken for USD.
QUOTE_ASSETS = (
    "FDUSD", "USDT", "USDC", "TUSD", "BUSD", "USDP", "DAI",
    "BTC", "ETH", "BNB", "EUR", "GBP", "AUD", "BRL", "TRY",
    "RUB", "BIDR", "IDRT", "NGN", "PLN", "RON", "ZAR", "JPY", "USD",
)


def quote_asset_for_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    for quote in QUOTE_ASSETS:
        if normalized.endswith(quote) and len(normalized) > len(quote):
            return quote
    return "UNKNOWN"


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return parsed if parsed.is_finite() else None


def value_position(position: dict[str, Any], prices: dict[str, str]) -> dict[str, Any]:
    """Add a real provider price and derived values without using binary floats."""
    symbol = str(position["symbol"]).upper()
    quantity = _decimal(position.get("quantity")) or Decimal("0")
    entry = _decimal(position.get("average_entry_price"))
    current = _decimal(prices.get(symbol))
    quote = quote_asset_for_symbol(symbol)
    market_value = quantity * current if current is not None else None
    cost_basis = quantity * entry if entry is not None else None
    pnl = market_value - cost_basis if market_value is not None and cost_basis is not None else None
    pnl_percent = (pnl / cost_basis * Decimal("100")) if pnl is not None and cost_basis not in (None, Decimal("0")) else None

    def string_or_none(value: Decimal | None) -> str | None:
        return format(value, "f") if value is not None else None

    return {
        "id": int(position["id"]),
        "symbol": symbol,
        "base_asset": symbol[:-len(quote)] if quote != "UNKNOWN" else None,
        "quote_asset": quote,
        "quantity": string_or_none(quantity),
        "average_entry_price": string_or_none(entry),
        "current_price": string_or_none(current),
        "market_value": string_or_none(market_value),
        "cost_basis": string_or_none(cost_basis),
        "unrealized_pnl": string_or_none(pnl),
        "unrealized_pnl_percent": string_or_none(pnl_percent),
        "valuation_status": "available" if current is not None else "unavailable",
        "source": "Binance Spot" if current is not None else None,
    }


def build_portfolio_response(positions: list[dict[str, Any]], prices: dict[str, str], updated_at: str | None) -> dict[str, Any]:
    items = [value_position(position, prices) for position in positions]
    grouped: dict[str, dict[str, Any]] = {}
    for item in items:
        quote = item["quote_asset"]
        group = grouped.setdefault(quote, {
            "quote_asset": quote,
            "market_value": Decimal("0"),
            "cost_basis": Decimal("0"),
            "unrealized_pnl": Decimal("0"),
            "priced_positions": 0,
            "positions_with_entry_price": 0,
            "positions_with_pnl": 0,
            "unpriced_positions": 0,
        })
        market_value = _decimal(item["market_value"])
        cost_basis = _decimal(item["cost_basis"])
        pnl = _decimal(item["unrealized_pnl"])
        if market_value is not None:
            group["market_value"] += market_value
            group["priced_positions"] += 1
        else:
            group["unpriced_positions"] += 1
        if cost_basis is not None:
            group["cost_basis"] += cost_basis
            group["positions_with_entry_price"] += 1
        if pnl is not None:
            group["unrealized_pnl"] += pnl
            group["positions_with_pnl"] += 1

    totals = []
    for quote, group in sorted(grouped.items()):
        totals.append({
            "quote_asset": quote,
            "market_value": format(group["market_value"], "f"),
            "cost_basis": format(group["cost_basis"], "f") if group["positions_with_entry_price"] else None,
            "unrealized_pnl": format(group["unrealized_pnl"], "f") if group["positions_with_pnl"] else None,
            "priced_positions": group["priced_positions"],
            "positions_with_entry_price": group["positions_with_entry_price"],
            "positions_with_pnl": group["positions_with_pnl"],
            "unpriced_positions": group["unpriced_positions"],
        })
    return {
        "source": "Binance Spot",
        "updated_at": updated_at,
        "items": items,
        "totals_by_quote_asset": totals,
        "warnings": [],
    }
