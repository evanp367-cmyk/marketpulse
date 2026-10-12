"""Deterministic movement events from closed Binance Spot candles only."""
from datetime import datetime, timezone
from math import isfinite
from statistics import median

WINDOW_MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
BASELINE_CANDLES = 20
SUPPORTED_EVENT_TYPES = ("price_surge", "price_drop", "volume_anomaly")


def _number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def _event(candles: list[dict], index: int, symbol: str, interval: str, now_ms: int) -> dict | None:
    current = candles[index]
    previous = candles[index - 1]
    price = _number(current.get("close"))
    old_price = _number(previous.get("close"))
    high = _number(current.get("high"))
    low = _number(current.get("low"))
    quote_volume = _number(current.get("quote_volume"))
    close_ms = current.get("close_time")
    baseline = [_number(row.get("quote_volume")) for row in candles[index - BASELINE_CANDLES:index]]
    if (not isinstance(close_ms, int) or close_ms > now_ms or price is None or old_price is None
            or high is None or low is None or quote_volume is None or price <= 0 or old_price <= 0
            or low <= 0 or high < low or not low <= price <= high or quote_volume < 0
            or any(value is None or value <= 0 for value in baseline)):
        return None
    reference = median(baseline)
    change = (price / old_price - 1) * 100
    volume_ratio = quote_volume / reference
    event_type = None
    if change >= 3 and volume_ratio >= 1.5:
        event_type = "price_surge"
    elif change <= -3 and volume_ratio >= 1.5:
        event_type = "price_drop"
    elif volume_ratio >= 3:
        event_type = "volume_anomaly"
    if event_type is None:
        return None
    age_seconds = max(0, (now_ms - close_ms) // 1000)
    momentum = round(min(40, abs(change) * 5))
    volume = round(min(30, max(0, volume_ratio - 1) * 10))
    range_score = round(min(20, (high / low - 1) * 200))
    freshness = 10 if age_seconds <= 2 * WINDOW_MS[interval] // 1000 else 0
    quote_asset = "USDT" if symbol.endswith("USDT") else "USDC" if symbol.endswith("USDC") else None
    return {
        "key": f"{symbol}:{interval}:{event_type}:{close_ms}",
        "type": event_type, "symbol": symbol, "interval": interval,
        "source": "Binance Spot klines", "detected_at": datetime.fromtimestamp(close_ms / 1000, timezone.utc).isoformat(),
        "price": price, "change_percent": round(change, 4), "direction": "up" if change > 0 else "down" if change < 0 else "flat",
        "high": high, "low": low, "quote_volume": quote_volume, "quote_asset": quote_asset,
        "volume_ratio": round(volume_ratio, 3), "baseline_candles": BASELINE_CANDLES,
        "duration_seconds": WINDOW_MS[interval] // 1000, "age_seconds": age_seconds,
        "strength": momentum + volume + range_score + freshness,
        "strength_components": {"momentum": momentum, "volume": volume, "range": range_score, "freshness": freshness},
        "reason_codes": (["price_change_at_least_3pct", "volume_at_least_1_5x"] if event_type in ("price_surge", "price_drop")
                         else ["volume_at_least_3x"]),
        "warnings": (["wide_candle_range"] if high / low - 1 >= .08 else [])
                    + (["stale_closed_candle"] if freshness == 0 else []),
    }


def detect_movements(candles: list[dict], symbol: str, interval: str, now: datetime | None = None) -> dict:
    """Return the latest event and a bounded history; never infer live/trade-level data."""
    if interval not in WINDOW_MS:
        raise ValueError("Unsupported movement interval")
    now = now or datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    closed = [row for row in candles if row.get("closed") and isinstance(row.get("close_time"), int)
              and row["close_time"] <= now_ms]
    events = []
    for index in range(BASELINE_CANDLES, len(closed)):
        event = _event(closed, index, symbol.upper(), interval, now_ms)
        if event is not None:
            events.append(event)
    latest_close = closed[-1]["close_time"] if closed else None
    current = events[-1] if events and latest_close and events[-1]["key"].endswith(f":{latest_close}") else None
    return {"source": "Binance Spot klines", "symbol": symbol.upper(), "interval": interval,
            "computed_at": now.isoformat(), "latest_closed_at": datetime.fromtimestamp(latest_close / 1000, timezone.utc).isoformat() if latest_close else None,
            "current": current, "history": list(reversed(events[-12:])),
            "rules": {"price_change_percent": 3, "price_event_min_volume_ratio": 1.5,
                      "volume_anomaly_ratio": 3, "volume_baseline_candles": BASELINE_CANDLES,
                      "strength_formula": "min(40, abs(change_pct)*5) + min(30, max(0, volume_ratio-1)*10) + min(20, (high/low-1)*200) + freshness(10 if age <= 2 intervals else 0)"},
            "disclaimer": "Historical market event, not a prediction or a probability of profit."}
