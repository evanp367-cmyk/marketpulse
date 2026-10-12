"""Market events and explicit per-user Telegram subscriptions."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import current_user
from backend.app.core.config import settings
from backend.app.db.session import get_session
from backend.app.models.models import User
from backend.app.providers.binance import BinancePublicProvider, MarketDataError
from backend.app.signals.intelligence import WINDOW_MS, detect_movements
from backend.app.signals.models import SignalDelivery, SignalSubscription

router = APIRouter(prefix="/api/signals", tags=["signal intelligence"])
provider = BinancePublicProvider()


def subscription_response(row: SignalSubscription) -> dict:
    return {"id": row.id, "symbol": row.symbol, "interval": row.interval,
            "enabled": row.enabled, "cooldown_seconds": row.cooldown_seconds,
            "last_notified_at": row.last_notified_at}


@router.get("/movements")
async def movements(
    symbol: str = Query("BTCUSDT", min_length=5, max_length=30, pattern="^[A-Za-z0-9]+$"),
    interval: str = Query("1h"),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    if interval not in WINDOW_MS:
        raise HTTPException(422, detail="Unsupported movement interval")
    symbol = symbol.upper()
    try:
        candles = await provider.klines(symbol, interval, 100)
    except MarketDataError as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    result = detect_movements(candles, symbol, interval)
    sub = await session.scalar(select(SignalSubscription).where(
        SignalSubscription.user_id == user.id, SignalSubscription.symbol == symbol,
        SignalSubscription.interval == interval,
    ))
    result["subscription"] = subscription_response(sub) if sub else None
    result["delivery_enabled"] = settings.signal_delivery_enabled
    return result


class SubscriptionInput(BaseModel):
    symbol: str = Field(min_length=5, max_length=30, pattern="^[A-Za-z0-9]+$")
    interval: str = Field(default="1h")


@router.get("/subscriptions")
async def subscriptions(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(SignalSubscription).where(
        SignalSubscription.user_id == user.id).order_by(SignalSubscription.id.desc()))).all()
    return {"items": [subscription_response(row) for row in rows], "delivery_enabled": settings.signal_delivery_enabled}


@router.post("/subscriptions")
async def subscribe(payload: SubscriptionInput, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    if payload.interval not in WINDOW_MS:
        raise HTTPException(422, detail="Unsupported movement interval")
    symbol = payload.symbol.upper()
    await session.scalar(select(User.id).where(User.id == user.id).with_for_update())
    existing = await session.scalar(select(SignalSubscription).where(
        SignalSubscription.user_id == user.id, SignalSubscription.symbol == symbol,
        SignalSubscription.interval == payload.interval,
    ))
    if existing and existing.enabled:
        return subscription_response(existing)
    count = await session.scalar(select(func.count(SignalSubscription.id)).where(
        SignalSubscription.user_id == user.id, SignalSubscription.enabled.is_(True)))
    if count >= 3:
        raise HTTPException(403, detail="Maximum 3 market-event subscriptions per user")
    if existing:
        existing.enabled = True
        await session.commit()
        return subscription_response(existing)
    try:
        candles = await provider.klines(symbol, payload.interval, 1)
    except MarketDataError as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    if not candles:
        raise HTTPException(422, detail="No Binance Spot candles for this symbol")
    row = SignalSubscription(user_id=user.id, symbol=symbol, interval=payload.interval)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return subscription_response(row)


@router.delete("/subscriptions/{subscription_id}")
async def unsubscribe(subscription_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    row = await session.scalar(select(SignalSubscription).where(
        SignalSubscription.id == subscription_id, SignalSubscription.user_id == user.id,
    ))
    if row is None:
        raise HTTPException(404, detail="Signal subscription not found")
    row.enabled = False
    await session.commit()
    return {"enabled": False}


@router.get("/deliveries")
async def delivery_history(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(SignalDelivery).where(SignalDelivery.user_id == user.id)
                                  .order_by(SignalDelivery.id.desc()).limit(30))).all()
    return {"items": [{"id": row.id, "event": row.snapshot, "status": row.status,
                       "created_at": row.created_at, "delivered_at": row.delivered_at}
                      for row in rows]}
