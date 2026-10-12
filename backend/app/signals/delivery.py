"""Bounded, opt-in Telegram delivery for market events.

Price alerts keep their own evaluator and AlertEvent history. Telegram has no
sendMessage idempotency key; a crash after acceptance can still cause a retry.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter, TelegramUnauthorizedError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.models.models import User
from backend.app.providers.binance import BinancePublicProvider, MarketDataError
from backend.app.signals.intelligence import WINDOW_MS, detect_movements
from backend.app.signals.models import SignalDelivery, SignalSubscription

logger = logging.getLogger(__name__)
MAX_PAIRS_PER_CYCLE = 20
MAX_EVENTS_PER_CYCLE = 20
MAX_USER_EVENTS_PER_HOUR = 4
DELIVERY_LEASE_SECONDS = 90
DELIVERY_TIMEOUT_SECONDS = 15


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def signal_message(event: dict) -> str:
    names = {"price_surge": "Резкий рост", "price_drop": "Резкое снижение", "volume_anomaly": "Аномальный объём"}
    reason = (f"Цена изменилась на {event['change_percent']:+.2f}% за {event['interval']}; "
              f"объём {event['volume_ratio']:.2f}× к медиане 20 предыдущих свечей"
              if event["type"] != "volume_anomaly" else
              f"Объём {event['volume_ratio']:.2f}× к медиане 20 предыдущих свечей")
    unit = event.get("quote_asset") or "котируемой валюты"
    return (f"MarketPulse / Market Movement\n{event['symbol']} · {names[event['type']]}\n"
            f"Изменение: {event['change_percent']:+.2f}%\n"
            f"Цена закрытия: {event['price']:.8g}\n"
            f"Объём свечи: {event['quote_volume']:.8g} {unit}\n"
            f"Время: {event['detected_at']}\nПричина: {reason}\n"
            "Источник: Binance Spot, закрытая свеча. Не прогноз и не рекомендация.")


async def evaluate_movements(provider: BinancePublicProvider, now: datetime | None = None) -> int:
    now = as_utc(now or datetime.now(timezone.utc))
    async with SessionLocal() as session:
        subscriptions = (await session.scalars(select(SignalSubscription).where(SignalSubscription.enabled.is_(True))
                                                .order_by(SignalSubscription.last_checked_at.asc().nullsfirst(), SignalSubscription.id)
                                                .limit(100))).all()
        groups: dict[tuple[str, str], list[int]] = {}
        for sub in subscriptions:
            key = (sub.symbol, sub.interval)
            if key not in groups and len(groups) >= MAX_PAIRS_PER_CYCLE:
                continue
            groups.setdefault(key, []).append(sub.id)
        ids = [sub_id for group in groups.values() for sub_id in group]
        if ids:
            await session.execute(update(SignalSubscription).where(SignalSubscription.id.in_(ids)).values(last_checked_at=now))
            await session.commit()
    created = 0
    for (symbol, interval), sub_ids in groups.items():
        try:
            candles = await provider.klines(symbol, interval, 35)
            event = detect_movements(candles, symbol, interval, now)["current"]
        except (MarketDataError, ValueError) as exc:
            logger.warning("Signal check skipped for %s %s: %s", symbol, interval, type(exc).__name__)
            continue
        if event is None or event["age_seconds"] > 2 * WINDOW_MS[interval] // 1000:
            continue
        for sub_id in sub_ids:
            if created >= MAX_EVENTS_PER_CYCLE:
                return created
            async with SessionLocal() as session:
                sub = await session.get(SignalSubscription, sub_id, with_for_update=True)
                if sub is None or not sub.enabled or sub.symbol != symbol or sub.interval != interval:
                    continue
                last = as_utc(sub.last_notified_at) if sub.last_notified_at else None
                if last and now - last < timedelta(seconds=sub.cooldown_seconds):
                    continue
                hourly = await session.scalar(select(func.count(SignalDelivery.id)).where(
                    SignalDelivery.user_id == sub.user_id,
                    SignalDelivery.created_at >= now - timedelta(hours=1),
                    SignalDelivery.status.in_(("pending", "delivered")),
                ))
                if hourly >= MAX_USER_EVENTS_PER_HOUR:
                    continue
                key = f"{sub.id}:{event['key']}"
                if await session.scalar(select(SignalDelivery.id).where(SignalDelivery.event_key == key)):
                    continue
                sub.last_notified_at = now
                session.add(SignalDelivery(subscription_id=sub.id, user_id=sub.user_id, event_key=key,
                                           snapshot=event, created_at=now, next_attempt_at=now))
                try:
                    await session.commit()
                except IntegrityError:
                    await session.rollback()
                    continue
                created += 1
    return created


async def deliver_pending(bot, now: datetime | None = None) -> int:
    fixed_now = as_utc(now) if now else None
    checked_at = fixed_now or datetime.now(timezone.utc)
    async with SessionLocal() as session:
        ids = (await session.scalars(select(SignalDelivery.id).where(
            SignalDelivery.status == "pending", SignalDelivery.next_attempt_at <= checked_at,
        ).order_by(SignalDelivery.id).limit(MAX_EVENTS_PER_CYCLE))).all()
    delivered = 0
    for delivery_id in ids:
        checked_at = fixed_now or datetime.now(timezone.utc)
        async with SessionLocal() as session:
            claimed = await session.execute(update(SignalDelivery).where(
                SignalDelivery.id == delivery_id, SignalDelivery.status == "pending",
                SignalDelivery.next_attempt_at <= checked_at,
            ).values(next_attempt_at=checked_at + timedelta(seconds=DELIVERY_LEASE_SECONDS)))
            await session.commit()
            if claimed.rowcount != 1:
                continue
            row = await session.get(SignalDelivery, delivery_id)
            sub = await session.get(SignalSubscription, row.subscription_id) if row and row.subscription_id else None
            user = await session.get(User, row.user_id) if row else None
            if row is None or sub is None or user is None or not sub.enabled:
                if row:
                    row.status = "cancelled"
                    await session.commit()
                continue
            event = row.snapshot
            if (sub.interval not in WINDOW_MS or sub.symbol != event.get("symbol") or sub.interval != event.get("interval")
                    or checked_at - as_utc(row.created_at) > timedelta(seconds=max(1800, 2 * WINDOW_MS[sub.interval] // 1000))):
                row.status = "cancelled"
                row.error = "EventExpired"
                await session.commit()
                continue
            markup = None
            if settings.mini_app_url.startswith("https://"):
                url = settings.mini_app_url.split("#", 1)[0] + "#signals"
                markup = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="Открыть в MarketPulse", web_app=WebAppInfo(url=url))
                ]])
            try:
                await asyncio.wait_for(bot.send_message(int(user.telegram_id), signal_message(event),
                                                        reply_markup=markup, request_timeout=DELIVERY_TIMEOUT_SECONDS),
                                       timeout=DELIVERY_TIMEOUT_SECONDS + 1)
            except TelegramRetryAfter as exc:
                retry_at = checked_at + timedelta(seconds=max(1, exc.retry_after) + 1)
                row.next_attempt_at = retry_at
                row.error = "TelegramRetryAfter"
                await session.flush()
                await session.execute(update(SignalDelivery).where(
                    SignalDelivery.status == "pending", SignalDelivery.next_attempt_at < retry_at,
                ).values(next_attempt_at=retry_at))
                await session.commit()
                break
            except Exception as exc:
                row.attempts += 1
                row.error = type(exc).__name__[:200]
                if isinstance(exc, (TelegramBadRequest, TelegramForbiddenError, TelegramUnauthorizedError, ValueError)) or row.attempts >= 3:
                    row.status = "failed"
                else:
                    row.next_attempt_at = checked_at + timedelta(seconds=30 * 2 ** (row.attempts - 1))
                logger.warning("Signal delivery failed for event %s: %s", row.id, type(exc).__name__)
            else:
                row.status = "delivered"
                row.delivered_at = datetime.now(timezone.utc)
                row.error = None
                delivered += 1
            await session.commit()
    return delivered


async def run_signal_delivery(bot):
    provider = BinancePublicProvider()
    try:
        while True:
            try:
                await evaluate_movements(provider)
                await deliver_pending(bot)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Signal delivery cycle failed")
            await asyncio.sleep(60)
    finally:
        await provider.aclose()
