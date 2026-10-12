"""Price alerts: ownership, crossing, cooldown and delivery are checked locally."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from backend.app.alerts import engine as alerts
from backend.app.models.models import AlertEvent
from backend.tests.test_api_workflow import client, telegram_headers


class Prices:
    def __init__(self):
        self.price = "90"

    async def ticker_prices(self, symbols):
        assert symbols == ["BTCUSDT"]
        return {"BTCUSDT": self.price}


class Bot:
    def __init__(self):
        self.messages = []
        self.fail = False

    async def send_message(self, chat_id, text):
        if self.fail:
            raise RuntimeError("test delivery failure")
        self.messages.append((chat_id, text))


@pytest.mark.asyncio
async def test_alert_crossing_delivery_history_and_ownership(client, monkeypatch):
    http, sessions = client
    monkeypatch.setattr(alerts, "SessionLocal", sessions)
    owner, stranger = telegram_headers(42), telegram_headers(43)
    invalid = await http.post("/api/alerts", headers=owner, json={
        "name": "invalid", "symbol": "BTCUSDT",
        "condition": {"type": "price", "direction": "above", "threshold": -1},
    })
    assert invalid.status_code == 422
    created = await http.post("/api/alerts", headers=owner, json={
        "name": "BTC target", "symbol": "btcusdt",
        "condition": {"type": "price", "direction": "above", "threshold": "100"},
        "cooldown_seconds": 900,
    })
    assert created.status_code == 200
    rule_id = created.json()["id"]
    assert (await http.get("/api/alerts", headers=stranger)).json()["items"] == []
    assert (await http.delete(f"/api/alerts/{rule_id}", headers=stranger)).status_code == 404

    provider, bot = Prices(), Bot()
    now = datetime(2026, 10, 12, tzinfo=timezone.utc)
    assert await alerts.evaluate_prices(provider, now) == 0
    provider.price = "101"
    assert await alerts.evaluate_prices(provider, now + timedelta(seconds=30)) == 1
    assert await alerts.evaluate_prices(provider, now + timedelta(seconds=60)) == 0
    assert await alerts.deliver_pending(bot, now + timedelta(seconds=30)) == 1
    assert len(bot.messages) == 1 and bot.messages[0][0] == 42
    assert "Binance Spot" in bot.messages[0][1]
    assert (await http.get("/api/alerts/history", headers=owner)).json()["items"][0]["status"] == "delivered"
    assert (await http.get("/api/alerts/history", headers=stranger)).json()["items"] == []
    provider.price = "99"
    await alerts.evaluate_prices(provider, now + timedelta(seconds=100))
    provider.price = "102"
    assert await alerts.evaluate_prices(provider, now + timedelta(seconds=150)) == 0  # cooldown
    provider.price = "99"
    await alerts.evaluate_prices(provider, now + timedelta(seconds=900))
    provider.price = "102"
    assert await alerts.evaluate_prices(provider, now + timedelta(seconds=950)) == 1

    updated = await http.put(f"/api/alerts/{rule_id}", headers=owner, json={
        "name": "BTC target", "symbol": "BTCUSDT", "enabled": False,
        "condition": {"type": "price", "direction": "above", "threshold": "100"},
        "cooldown_seconds": 900,
    })
    assert updated.status_code == 200 and not updated.json()["enabled"]
    assert await alerts.deliver_pending(bot, now + timedelta(seconds=950)) == 0
    async with sessions() as session:
        events = (await session.execute(select(AlertEvent).order_by(AlertEvent.id))).scalars().all()
        assert [event.status for event in events] == ["delivered", "cancelled"]
    assert (await http.delete(f"/api/alerts/{rule_id}", headers=owner)).status_code == 200


@pytest.mark.asyncio
async def test_failed_delivery_is_retried_and_recorded(client, monkeypatch):
    http, sessions = client
    monkeypatch.setattr(alerts, "SessionLocal", sessions)
    headers = telegram_headers(99)
    response = await http.post("/api/alerts", headers=headers, json={
        "name": "Below", "symbol": "BTCUSDT",
        "condition": {"type": "price", "direction": "below", "threshold": "100"},
    })
    assert response.status_code == 200
    now = datetime(2026, 10, 12, tzinfo=timezone.utc)
    provider, bot = Prices(), Bot()
    assert await alerts.evaluate_prices(provider, now) == 1
    bot.fail = True
    assert await alerts.deliver_pending(bot, now) == 0
    assert await alerts.deliver_pending(bot, now + timedelta(seconds=10)) == 0
    bot.fail = False
    assert await alerts.deliver_pending(bot, now + timedelta(seconds=31)) == 1
    history = (await http.get("/api/alerts/history", headers=headers)).json()["items"]
    assert history[0]["attempts"] == 1 and history[0]["status"] == "delivered"
