"""HTTP/DB regressions; all data is local and Telegram calls use a test transport."""
import asyncio
import hashlib
import hmac
import json
import time
from functools import partial
from urllib.parse import urlencode

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app import main as api_module
from backend.app.db import session as db_module
from backend.app.models.models import Base, Subscription, User


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite3'}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    monkeypatch.setattr(db_module, "SessionLocal", sessions)
    monkeypatch.setattr(api_module.settings, "environment", "development")
    monkeypatch.setattr(api_module.settings, "dev_auth_enabled", True)
    monkeypatch.setattr(api_module.settings, "telegram_bot_token", "123:test-only-token")
    monkeypatch.setattr(api_module.settings, "telegram_pro_price_stars", 250)

    async def session_dependency():
        async with sessions() as session:
            yield session

    api_module.app.dependency_overrides[db_module.get_session] = session_dependency
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api_module.app, raise_app_exceptions=False),
            base_url="http://test",
        ) as test_client:
            yield test_client, sessions
    finally:
        api_module.app.dependency_overrides.pop(db_module.get_session, None)
        await engine.dispose()


def telegram_headers(user_id):
    data = {"auth_date": str(int(time.time())), "user": json.dumps({"id": user_id})}
    check = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret = hmac.new(b"WebAppData", api_module.settings.telegram_bot_token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return {"X-Telegram-Init-Data": urlencode(data)}


@pytest.mark.asyncio
async def test_concurrent_first_login_creates_one_user_without_server_errors(client):
    http, sessions = client
    responses = await asyncio.gather(*(
        http.get("/api/me", headers=telegram_headers(42)) for _ in range(20)
    ))
    assert [r.status_code for r in responses] == [200] * 20
    assert all(r.json()["telegram_id"] == "42" for r in responses)
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.asyncio
async def test_concurrent_first_plan_requests_create_one_subscription(client):
    http, sessions = client
    headers = telegram_headers(42)
    assert (await http.get("/api/me", headers=headers)).status_code == 200
    responses = await asyncio.gather(*(
        http.get("/api/plans", headers=headers) for _ in range(20)
    ))
    assert [r.status_code for r in responses] == [200] * 20
    assert all(r.json()["current_plan"] == "free" for r in responses)
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Subscription)) == 1


@pytest.mark.asyncio
async def test_portfolio_is_scoped_to_verified_telegram_user(client, monkeypatch):
    http, _ = client

    async def unavailable_prices(symbols):
        raise api_module.MarketDataError("Test provider unavailable")

    monkeypatch.setattr(api_module.provider, "ticker_prices", unavailable_prices)
    owner, stranger = telegram_headers(42), telegram_headers(43)
    created = await http.post("/api/portfolio", headers=owner, json={
        "symbol": "BTCUSDT", "quantity": "0.1", "average_entry_price": "50000",
    })
    assert created.status_code == 200
    position_id = created.json()["id"]
    own = (await http.get("/api/portfolio", headers=owner)).json()
    assert own["items"][0]["id"] == position_id
    assert own["totals_by_quote_asset"][0]["market_value"] is None
    assert own["warnings"]
    assert (await http.get("/api/portfolio", headers=stranger)).json()["items"] == []
    assert (await http.delete(f"/api/portfolio/{position_id}", headers=stranger)).status_code == 404
    assert (await http.delete(f"/api/portfolio/{position_id}", headers=owner)).status_code == 200


@pytest.mark.asyncio
async def test_development_identity_is_rejected_in_production(client, monkeypatch):
    http, _ = client
    monkeypatch.setattr(api_module.settings, "environment", "production")
    assert (await http.get("/api/me", headers={"X-Dev-User": "local-dev"})).status_code == 401
    assert (await http.get("/api/me", headers=telegram_headers(42))).status_code == 200


@pytest.mark.asyncio
async def test_invoice_is_one_time_250_stars_without_recurring_billing(client, monkeypatch):
    http, _ = client
    requests = []

    def telegram(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "result": "https://t.me/$test-only"})

    monkeypatch.setattr(api_module.httpx, "AsyncClient", partial(
        httpx.AsyncClient, transport=httpx.MockTransport(telegram),
    ))
    response = await http.post("/api/subscription/pro/invoice", headers=telegram_headers(42))
    assert response.status_code == 200
    assert len(requests) == 1
    body = json.loads(requests[0].content)
    assert "subscription_period" not in body
    assert body["currency"] == "XTR"
    assert body["prices"] == [{"label": "MarketPulse Pro · 30 days", "amount": 250}]
    assert body["provider_token"] == ""
    assert body["payload"].startswith("marketpulse_pro_month_42_")


@pytest.mark.asyncio
async def test_development_user_cannot_start_payment(client):
    http, _ = client
    response = await http.post("/api/subscription/pro/invoice", headers={"X-Dev-User": "local-dev"})
    assert response.status_code == 400
