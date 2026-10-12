"""Realistic closed-candle fixtures; Telegram and Binance are never contacted."""
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app import main as api_module
from backend.app.core.auth import current_user
from backend.app.db import session as db_module
from backend.app.models.models import Base, User
from backend.app.signals import api as signal_api
from backend.app.signals import delivery
from backend.app.signals.intelligence import detect_movements
from backend.app.signals.models import SignalDelivery, SignalSubscription

NOW = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)


def candles(last_price=104, last_volume=200, *, last_closed=True):
    result = []
    for index in range(21):
        price = last_price if index == 20 else 100
        volume = last_volume if index == 20 else 100
        close_at = NOW - timedelta(hours=20 - index, seconds=10)
        result.append({"close_time": int(close_at.timestamp() * 1000), "open": 100,
                       "high": max(price, 100) + 1, "low": min(price, 100) - 1,
                       "close": price, "volume": volume, "quote_volume": volume,
                       "closed": index != 20 or last_closed})
    return result


@pytest.mark.parametrize("price,volume,kind", [
    (104, 200, "price_surge"), (96, 200, "price_drop"), (100, 350, "volume_anomaly"),
])
def test_events_use_only_verified_closed_candles(price, volume, kind):
    result = detect_movements(candles(price, volume), "BTCUSDT", "1h", NOW)
    event = result["current"]
    assert event["type"] == kind
    assert event["source"] == "Binance Spot klines"
    assert event["price"] == price
    assert event["quote_volume"] == volume
    assert event["volume_ratio"] == volume / 100
    assert event["strength"] == sum(event["strength_components"].values())
    assert len(result["history"]) == 1
    assert detect_movements(candles(price, volume, last_closed=False), "BTCUSDT", "1h", NOW)["current"] is None


def test_missing_or_invalid_volume_never_invents_event():
    rows = candles()
    del rows[-1]["quote_volume"]
    assert detect_movements(rows, "BTCUSDT", "1h", NOW)["current"] is None
    rows[-1]["quote_volume"] = float("nan")
    assert detect_movements(rows, "BTCUSDT", "1h", NOW)["current"] is None


@pytest.mark.asyncio
async def test_api_subscription_and_independent_delivery_journal(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'signals.sqlite3'}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    monkeypatch.setattr(db_module, "SessionLocal", sessions)
    monkeypatch.setattr(delivery, "SessionLocal", sessions)
    monkeypatch.setattr(api_module.settings, "environment", "development")
    monkeypatch.setattr(api_module.settings, "dev_auth_enabled", True)
    monkeypatch.setattr(api_module.settings, "signal_delivery_enabled", True)
    monkeypatch.setattr(api_module.settings, "mini_app_url", "https://example.com/marketpulse/")

    async def get_session():
        async with sessions() as session:
            yield session

    class Provider:
        async def klines(self, symbol, interval, limit):
            return candles()

    monkeypatch.setattr(signal_api, "provider", Provider())
    async with sessions() as session:
        user = User(telegram_id="12345")
        session.add(user)
        await session.commit()
        await session.refresh(user)
    api_module.app.dependency_overrides[db_module.get_session] = get_session
    api_module.app.dependency_overrides[current_user] = lambda: user
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api_module.app), base_url="http://test") as client:
            headers = {"X-Dev-User": "local-dev"}
            movement = await client.get("/api/signals/movements?symbol=BTCUSDT&interval=1h", headers=headers)
            assert movement.status_code == 200
            assert movement.json()["current"]["type"] == "price_surge"
            subscribed = await client.post("/api/signals/subscriptions", headers=headers,
                                           json={"symbol": "BTCUSDT", "interval": "1h"})
            assert subscribed.status_code == 200
            assert subscribed.json()["enabled"] is True
            subscription_id = subscribed.json()["id"]
            assert (await client.post("/api/signals/subscriptions", headers=headers,
                                      json={"symbol": "BTCUSDT", "interval": "1h"})).json()["id"] == subscription_id

            assert await delivery.evaluate_movements(Provider(), NOW) == 1
            assert await delivery.evaluate_movements(Provider(), NOW + timedelta(seconds=20)) == 0
            async with sessions() as session:
                assert await session.scalar(select(func.count()).select_from(SignalDelivery)) == 1
                assert await session.scalar(select(func.count()).select_from(SignalSubscription)) == 1

            class Bot:
                def __init__(self): self.calls = []
                async def send_message(self, *args, **kwargs): self.calls.append((args, kwargs))

            bot = Bot()
            assert await delivery.deliver_pending(bot, NOW + timedelta(seconds=25)) == 1
            assert len(bot.calls) == 1
            assert "BTCUSDT" in bot.calls[0][0][1]
            assert "Binance Spot" in bot.calls[0][0][1]
            assert bot.calls[0][1]["reply_markup"].inline_keyboard[0][0].text == "Открыть в MarketPulse"
            journal = await client.get("/api/signals/deliveries", headers=headers)
            assert journal.json()["items"][0]["status"] == "delivered"
            assert (await client.delete(f"/api/signals/subscriptions/{subscription_id}", headers=headers)).json() == {"enabled": False}
            assert await delivery.evaluate_movements(Provider(), NOW + timedelta(minutes=1)) == 0
    finally:
        api_module.app.dependency_overrides.pop(db_module.get_session, None)
        api_module.app.dependency_overrides.pop(current_user, None)
        await engine.dispose()


def test_telegram_message_has_no_unverified_metrics():
    event = detect_movements(candles(), "BTCUSDT", "1h", NOW)["current"]
    message = delivery.signal_message(event)
    assert "Справедливая цена" not in message
    assert "MEXC" not in message
    assert "DEX" not in message
    assert "Объём свечи" in message
