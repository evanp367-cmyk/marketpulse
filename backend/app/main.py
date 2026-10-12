from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field
from decimal import Decimal
from backend.app.core.config import settings, production_config_errors
from backend.app.core.auth import current_user
from backend.app.db.session import engine, get_session
from backend.app.models.models import Base, User, WatchlistItem, PortfolioPosition, AlertRule, Subscription, Payment
from backend.app.providers.binance import BinancePublicProvider, MarketDataError
from backend.app.providers.cbr import CBRDailyProvider, CBRDataError
from backend.app.providers.frankfurter import FrankfurterProvider, FrankfurterDataError, FrankfurterCurrencyPairUnavailable
from backend.app.portfolio.valuation import build_portfolio_response
from datetime import datetime, timezone, timedelta
import uuid
import httpx
from backend.app.indicators.calculations import ema, rsi, macd, bollinger
from backend.app.providers.news import latest_news

@asynccontextmanager
async def lifespan(app: FastAPI):
    _production_errors = production_config_errors(settings)
    if _production_errors:
        raise RuntimeError("Invalid production configuration: " + "; ".join(_production_errors))
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
app=FastAPI(title=settings.app_name,version="0.4.9",lifespan=lifespan)
# Vite may be opened as either localhost or 127.0.0.1. Browsers treat these
# as different origins, so allow both in local development even if an older
# .env file only lists one of them.
_allowed_origins = [x.strip().rstrip("/") for x in settings.cors_origins.split(",") if x.strip()]
if settings.environment == "development":
    for _origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        if _origin not in _allowed_origins:
            _allowed_origins.append(_origin)
app.add_middleware(CORSMiddleware,allow_origins=_allowed_origins,allow_credentials=False,allow_methods=["GET","POST","PUT","DELETE","OPTIONS"],allow_headers=["Content-Type","X-Telegram-Init-Data","X-Dev-User"])
provider=BinancePublicProvider()
cbr_provider=CBRDailyProvider()
frankfurter_provider=FrankfurterProvider()
@app.get("/health")
async def health(): return {"status":"ok","app":settings.app_name,"environment":settings.environment}
@app.get("/api/market/tickers")
async def tickers(symbols: str | None = None):
    try:return {"source":"Binance Spot","items":await provider.ticker_24h(symbols.split(",") if symbols else None)}
    except MarketDataError as exc: raise HTTPException(503,detail=str(exc)) from exc
@app.get("/api/fx/currencies")
async def fx_currency_catalog():
    """Currencies currently covered by the free Frankfurter reference-rate provider."""
    try:
        return await frankfurter_provider.currencies()
    except FrankfurterDataError as exc:
        raise HTTPException(503, detail=str(exc)) from exc

@app.get("/api/fx/world/daily")
async def world_daily_rates(
    base: str = Query(default="EUR", min_length=3, max_length=3, pattern="^[A-Za-z]{3}$"),
    quotes: str | None = Query(default=None, min_length=3, max_length=1000),
):
    """Daily reference rates from Frankfurter; without quotes returns all provider-supported quotes."""
    requested = [item.strip() for item in quotes.split(",") if item.strip()] if quotes else None
    try:
        return await frankfurter_provider.daily_rates(base, requested)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    except FrankfurterDataError as exc:
        raise HTTPException(503, detail=str(exc)) from exc

@app.get("/api/fx/convert")
async def convert_currency(
    amount: Decimal = Query(default=Decimal("1"), gt=0, le=Decimal("1000000000000000")),
    from_currency: str = Query(default="USD", min_length=3, max_length=3, pattern="^[A-Za-z]{3}$"),
    to_currency: str = Query(default="EUR", min_length=3, max_length=3, pattern="^[A-Za-z]{3}$"),
):
    """Convert currency using Frankfurter's daily reference rate, not a live Forex quote."""
    try:
        return await frankfurter_provider.convert(amount, from_currency, to_currency)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    except FrankfurterCurrencyPairUnavailable as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    except FrankfurterDataError as exc:
        raise HTTPException(503, detail=str(exc)) from exc

@app.get("/api/fx/cbr/daily")
async def cbr_daily_rates(symbols: str | None = Query(default=None, description="Optional comma-separated ISO currency codes; omit to return all currencies published by the Bank of Russia")):
    """Daily official Bank of Russia reference rates. Not realtime Forex quotes."""
    requested = symbols.split(",") if symbols else None
    try:
        return await cbr_provider.daily_rates(requested)
    except CBRDataError as exc:
        raise HTTPException(503, detail=str(exc)) from exc

@app.get("/api/market/klines")
async def klines(
    symbol: str = Query("BTCUSDT", min_length=2, max_length=30, pattern="^[A-Za-z0-9]+$"),
    interval: str = Query("1h", min_length=2, max_length=3),
    limit: int = Query(300, ge=1, le=1000),
):
    try:return {"source":"Binance Spot","symbol":symbol.upper(),"interval":interval,"items":await provider.klines(symbol,interval,limit)}
    except ValueError as exc:raise HTTPException(422,detail=str(exc)) from exc
    except MarketDataError as exc:raise HTTPException(503,detail=str(exc)) from exc

@app.get("/api/signals")
async def market_signals(symbol: str = Query(default="BTCUSDT", min_length=5, max_length=30, pattern="^[A-Za-z0-9]+$"), interval: str = "1h", user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    """Educational technical overview calculated from real Binance Spot candles; not a buy/sell instruction."""
    try:
        candles = await provider.klines(symbol.upper(), interval, 220)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    except MarketDataError as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    closed = [c for c in candles if c.get("closed")]
    closes = [float(c["close"]) for c in closed]
    if len(closes) < 60:
        raise HTTPException(503, detail="Not enough closed candles to calculate stable indicators")
    e20, e50 = ema(closes, 20), ema(closes, 50)
    rsi_values = rsi(closes, 14)
    macd_values = macd(closes)
    bands = bollinger(closes, 20)
    i = len(closes) - 1
    current_rsi = float(rsi_values[i]) if rsi_values[i] is not None else 50.0
    current_macd = macd_values["histogram"][i]
    subscription = await _get_subscription(session, user)
    is_pro = bool(subscription.plan_code == "pro" and subscription.status == "active" and (subscription.ends_at is None or (subscription.ends_at.replace(tzinfo=timezone.utc) if subscription.ends_at.tzinfo is None else subscription.ends_at) > datetime.now(timezone.utc)))
    score = 0
    reasons = []
    if e20[i] is not None and e50[i] is not None:
        if e20[i] > e50[i]:
            score += 1
            reasons.append("EMA 20 выше EMA 50: краткосрочный тренд сильнее долгосрочного")
        elif e20[i] < e50[i]:
            score -= 1
            reasons.append("EMA 20 ниже EMA 50: краткосрочный тренд слабее долгосрочного")
        else:
            reasons.append("EMA 20 и EMA 50 совпадают: направленного преимущества нет")
    if current_macd is not None:
        if current_macd > 0:
            score += 1
            reasons.append("MACD histogram выше нуля: импульс положительный")
        elif current_macd < 0:
            score -= 1
            reasons.append("MACD histogram ниже нуля: импульс отрицательный")
        else:
            reasons.append("MACD histogram около нуля: выраженный импульс отсутствует")
    if current_rsi >= 70: score -= 1; reasons.append("RSI ≥ 70: рынок может быть перегрет")
    elif current_rsi <= 30: score += 1; reasons.append("RSI ≤ 30: рынок может быть перепродан")
    else: reasons.append("RSI находится между 30 и 70")
    label = "bullish_bias" if score >= 2 else "bearish_bias" if score <= -2 else "mixed"
    candle_close_ms = closed[-1].get("close_time")
    candle_closed_at = (
        datetime.fromtimestamp(candle_close_ms / 1000, timezone.utc).isoformat()
        if candle_close_ms is not None
        else None
    )
    return {"symbol": symbol.upper(), "interval": interval, "plan": "pro" if is_pro else "free", "pro_features": is_pro, "source": "Binance Spot klines", "computed_at": datetime.now(timezone.utc).isoformat(), "candle_closed_at": candle_closed_at, "price": closes[-1], "label": label, "score": score, "indicators": {"rsi14": round(current_rsi, 2), "ema20": round(float(e20[i]), 8) if e20[i] is not None else None, "ema50": round(float(e50[i]), 8) if e50[i] is not None else None, "macd_histogram": round(float(current_macd), 8) if current_macd is not None else None, "bollinger_upper": round(float(bands["upper"][i]), 8) if is_pro and bands["upper"][i] is not None else None, "bollinger_middle": round(float(bands["middle"][i]), 8) if is_pro and bands["middle"][i] is not None else None, "bollinger_lower": round(float(bands["lower"][i]), 8) if is_pro and bands["lower"][i] is not None else None}, "reasons": reasons, "disclaimer": "Educational indicator summary only. It is not a personalized recommendation or a guarantee of future performance."}

@app.get("/api/news")
async def news_feed(limit: int = Query(default=20, ge=1, le=50), user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
    sub_end = subscription.ends_at.replace(tzinfo=timezone.utc) if subscription and subscription.ends_at and subscription.ends_at.tzinfo is None else (subscription.ends_at if subscription else None)
    is_pro = bool(subscription and subscription.plan_code == "pro" and subscription.status == "active" and (sub_end is None or sub_end > datetime.now(timezone.utc)))
    result = await latest_news(limit if is_pro else min(limit, 5))
    result["plan"] = "pro" if is_pro else "free"
    result["limit"] = 50 if is_pro else 5
    return result

async def _get_subscription(session: AsyncSession, user: User):
    sub = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
    if sub is None:
        sub = Subscription(user_id=user.id, plan_code="free", status="active", provider="none")
        session.add(sub)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            sub = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
            if sub is None:
                raise
        else:
            await session.refresh(sub)
    end = sub.ends_at.replace(tzinfo=timezone.utc) if sub.ends_at and sub.ends_at.tzinfo is None else sub.ends_at
    if sub.plan_code == "pro" and end and end <= datetime.now(timezone.utc):
        sub.plan_code = "free"; sub.status = "expired"; await session.commit()
    return sub

@app.get("/api/plans")
async def plans(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    sub = await _get_subscription(session, user)
    return {"current_plan": sub.plan_code, "status": sub.status, "ends_at": sub.ends_at.isoformat() if sub.ends_at else None, "payment_provider": sub.provider, "plans": [{"code":"free","name":"Free","price":0,"currency":"XTR","features":["Рынок и базовые графики","Ручной портфель","Технический обзор по выбранной паре","До 5 новостных заголовков"]},{"code":"pro","name":"Pro","price":settings.telegram_pro_price_stars,"currency":"XTR","price_unit":"Stars / month","features":["До 50 новостных заголовков","Полосы Боллинджера в техническом обзоре","До 20 сохранённых правил алертов (автоматическая проверка и доставка пока не реализованы)","До 100 ручных позиций в портфеле"]}], "note":"Цена Pro задаётся через TELEGRAM_PRO_PRICE_STARS. Stars не равны рублям."}

@app.post("/api/subscription/pro/invoice")
async def create_pro_invoice(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    if user.telegram_id == "dev-local-user":
        raise HTTPException(400, detail="Stars payments can only be started by a real Telegram user inside the Telegram Mini App. Local browser authentication is for development only.")
    if not settings.telegram_bot_token:
        raise HTTPException(503, detail="Telegram payment is not configured: set TELEGRAM_BOT_TOKEN")
    if settings.telegram_pro_price_stars < 1:
        raise HTTPException(503, detail="TELEGRAM_PRO_PRICE_STARS must be a positive integer")
    payload = f"marketpulse_pro_month_{user.telegram_id}_{uuid.uuid4().hex}"
    # A single payment grants 30 days. Recurring billing requires separate consent.
    body = {"title":"MarketPulse Pro · 30 days", "description":"Pro tools for market research. No guaranteed returns.", "payload":payload, "provider_token":"", "currency":"XTR", "prices":[{"label":"MarketPulse Pro · 30 days", "amount":settings.telegram_pro_price_stars}]}
    proxy_url = settings.telegram_proxy_url.strip()
    proxy_args = {"proxy": proxy_url} if proxy_url else {}
    telegram_api_base = settings.telegram_api_base_url.strip().rstrip("/") or "https://api.telegram.org"
    async with httpx.AsyncClient(timeout=10, **proxy_args) as client:
        try:
            response = await client.post(f"{telegram_api_base}/bot{settings.telegram_bot_token}/createInvoiceLink", json=body)
            response.raise_for_status(); data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(502, detail="Could not create Telegram Stars invoice") from exc
    if not data.get("ok") or not data.get("result"):
        raise HTTPException(502, detail="Telegram rejected the invoice request")
    return {"invoice_url":data["result"], "currency":"XTR", "amount":settings.telegram_pro_price_stars, "payload":payload}

@app.get("/api/subscription")
async def subscription_status(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    sub = await _get_subscription(session, user)
    return {"plan":sub.plan_code,"status":sub.status,"provider":sub.provider,"starts_at":sub.starts_at.isoformat() if sub.starts_at else None,"ends_at":sub.ends_at.isoformat() if sub.ends_at else None}

@app.get("/api/me")
async def me(user: User=Depends(current_user)):return {"telegram_id":user.telegram_id,"language":user.language,"theme":user.theme,"timezone":user.timezone}
class PreferenceInput(BaseModel):
    language: str | None = Field(default=None,pattern="^(ru|en)$")
    theme: str | None = Field(default=None,pattern="^(system|light|dark)$")
    timezone: str | None = Field(default=None,max_length=64)
@app.put("/api/me/preferences")
async def update_preferences(payload: PreferenceInput,user: User=Depends(current_user),session: AsyncSession=Depends(get_session)):
    result=await session.execute(select(User).where(User.id==user.id));row=result.scalar_one()
    for key,value in payload.model_dump(exclude_none=True).items():setattr(row,key,value)
    await session.commit();return {"language":row.language,"theme":row.theme,"timezone":row.timezone}
class WatchInput(BaseModel): symbol: str = Field(min_length=5,max_length=30,pattern="^[A-Za-z0-9]+$")
@app.get("/api/watchlist")
async def get_watchlist(user: User=Depends(current_user),session: AsyncSession=Depends(get_session)):
    r=await session.execute(select(WatchlistItem).where(WatchlistItem.user_id==user.id).order_by(WatchlistItem.symbol));return {"items":[x.symbol for x in r.scalars().all()]}
@app.post("/api/watchlist")
async def add_watchlist(payload: WatchInput,user: User=Depends(current_user),session: AsyncSession=Depends(get_session)):
    symbol=payload.symbol.upper();r=await session.execute(select(WatchlistItem).where(WatchlistItem.user_id==user.id,WatchlistItem.symbol==symbol))
    if r.scalar_one_or_none() is None:session.add(WatchlistItem(user_id=user.id,symbol=symbol));await session.commit()
    return {"symbol":symbol,"saved":True}
@app.delete("/api/watchlist/{symbol}")
async def delete_watchlist(symbol: str,user: User=Depends(current_user),session: AsyncSession=Depends(get_session)):
    r=await session.execute(select(WatchlistItem).where(WatchlistItem.user_id==user.id,WatchlistItem.symbol==symbol.upper()));item=r.scalar_one_or_none()
    if item:await session.delete(item);await session.commit()
    return {"symbol":symbol.upper(),"deleted":True}
class PositionInput(BaseModel):
    symbol: str = Field(min_length=2,max_length=30,pattern="^[A-Za-z0-9]+$")
    quantity: Decimal = Field(gt=0,max_digits=28,decimal_places=12)
    average_entry_price: Decimal | None = Field(default=None,gt=0,max_digits=28,decimal_places=12)
@app.get("/api/portfolio")
async def portfolio(user: User=Depends(current_user),session: AsyncSession=Depends(get_session)):
    r = await session.execute(
        select(PortfolioPosition)
        .where(PortfolioPosition.user_id == user.id)
        .order_by(PortfolioPosition.id.desc())
    )
    positions = [
        {
            "id": x.id,
            "symbol": x.symbol,
            "quantity": str(x.quantity),
            "average_entry_price": str(x.average_entry_price) if x.average_entry_price is not None else None,
        }
        for x in r.scalars().all()
    ]
    symbols = sorted({row["symbol"] for row in positions})
    warnings: list[str] = []
    prices: dict[str, str] = {}
    updated_at = None
    if symbols:
        try:
            prices = await provider.ticker_prices(symbols)
            updated_at = datetime.now(timezone.utc).isoformat() if prices else None
        except (MarketDataError, ValueError) as exc:
            # Preserve saved positions when the quote provider is down, but never invent prices.
            warnings.append(f"Current market prices are unavailable ({type(exc).__name__}).")
    response = build_portfolio_response(positions, prices, updated_at)
    response["warnings"] = warnings
    if symbols and not prices and not warnings:
        response["warnings"].append("No current prices were returned for the saved symbols.")
    return response
@app.post("/api/portfolio")
async def add_position(payload: PositionInput,user: User=Depends(current_user),session: AsyncSession=Depends(get_session)):
    sub = await _get_subscription(session, user)
    count_result = await session.execute(select(PortfolioPosition.id).where(PortfolioPosition.user_id == user.id))
    max_positions = 100 if sub.plan_code == "pro" and sub.status == "active" else 3
    if len(count_result.scalars().all()) >= max_positions:
        raise HTTPException(403, detail=f"Portfolio limit reached for {sub.plan_code} plan ({max_positions} positions). Upgrade to Pro for more positions.")
    row=PortfolioPosition(user_id=user.id,symbol=payload.symbol.upper(),quantity=payload.quantity,average_entry_price=payload.average_entry_price);session.add(row);await session.commit();await session.refresh(row);return {"id":row.id,"symbol":row.symbol,"quantity":str(row.quantity),"average_entry_price":str(row.average_entry_price) if row.average_entry_price is not None else None}
@app.delete("/api/portfolio/{position_id}")
async def delete_position(position_id:int,user:User=Depends(current_user),session:AsyncSession=Depends(get_session)):
    r=await session.execute(select(PortfolioPosition).where(PortfolioPosition.id==position_id,PortfolioPosition.user_id==user.id));row=r.scalar_one_or_none()
    if row is None:raise HTTPException(404,detail="Position not found")
    await session.delete(row);await session.commit();return {"deleted":True}
class AlertInput(BaseModel):
    name: str = Field(min_length=1,max_length=120)
    symbol: str = Field(min_length=5,max_length=30,pattern="^[A-Za-z0-9]+$")
    condition: dict
    cooldown_seconds: int = Field(default=900,ge=60,le=86400)
@app.get("/api/alerts")
async def alerts(user:User=Depends(current_user),session:AsyncSession=Depends(get_session)):
    r=await session.execute(select(AlertRule).where(AlertRule.user_id==user.id).order_by(AlertRule.id.desc()));return {"items":[{"id":x.id,"name":x.name,"symbol":x.symbol,"condition":x.condition,"enabled":x.enabled,"cooldown_seconds":x.cooldown_seconds} for x in r.scalars().all()]}
@app.post("/api/alerts")
async def create_alert(payload:AlertInput,user:User=Depends(current_user),session:AsyncSession=Depends(get_session)):
    sub = await _get_subscription(session, user)
    count_result = await session.execute(select(AlertRule).where(AlertRule.user_id == user.id))
    max_alerts = 20 if sub.plan_code == "pro" and sub.status == "active" else 2
    if len(count_result.scalars().all()) >= max_alerts:
        raise HTTPException(403, detail=f"Alert limit reached for {sub.plan_code} plan ({max_alerts}). Upgrade to Pro for more rules.")
    # Stored rule only. Evaluator/delivery is not implemented yet and is documented as unavailable.
    row=AlertRule(user_id=user.id,name=payload.name,symbol=payload.symbol.upper(),condition=payload.condition,cooldown_seconds=payload.cooldown_seconds);session.add(row);await session.commit();await session.refresh(row);return {"id":row.id,"enabled":row.enabled,"status":"saved_not_evaluated"}
