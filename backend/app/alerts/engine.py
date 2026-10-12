"""Evaluate opt-in spot price rules and deliver bounded Telegram notifications."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.models.models import AlertEvent, AlertRule, User
from backend.app.providers.binance import BinancePublicProvider, MarketDataError

logger = logging.getLogger(__name__)


def threshold(rule: AlertRule) -> tuple[str, Decimal] | None:
    condition = rule.condition
    if not isinstance(condition, dict) or condition.get("type") != "price":
        return None
    direction = condition.get("direction")
    if direction not in ("above", "below"):
        return None
    try:
        price = Decimal(str(condition["threshold"]))
    except (KeyError, InvalidOperation, TypeError):
        return None
    if not price.is_finite() or price <= 0:
        return None
    return direction, price


async def evaluate_prices(provider: BinancePublicProvider, now: datetime | None = None) -> int:
    """One market request per batch; no trigger when quotes are unavailable."""
    now = now or datetime.now(timezone.utc)
    async with SessionLocal() as session:
        rules = (await session.execute(select(AlertRule).where(AlertRule.enabled.is_(True)))).scalars().all()
    valid = [(rule, threshold(rule)) for rule in rules]
    valid = [(rule, target) for rule, target in valid if target is not None]
    if not valid:
        return 0
    try:
        prices = await provider.ticker_prices([rule.symbol for rule, _ in valid])
    except MarketDataError as exc:
        logger.warning("Alert price check skipped: %s", exc)
        return 0
    created = 0
    async with SessionLocal() as session:
        # Lock rows so two bot instances cannot record the same crossing together.
        ids = [rule.id for rule, _ in valid]
        locked = (await session.execute(
            select(AlertRule).where(AlertRule.id.in_(ids), AlertRule.enabled.is_(True)).with_for_update()
        )).scalars().all()
        for rule in locked:
            target = threshold(rule)
            raw = prices.get(rule.symbol)
            if target is None or raw is None:
                continue
            try:
                price = Decimal(raw)
            except InvalidOperation:
                continue
            if not price.is_finite() or price <= 0:
                continue
            direction, value = target
            met = price >= value if direction == "above" else price <= value
            if not met:
                rule.last_condition_met = False
                continue
            if rule.last_condition_met:
                continue
            rule.last_condition_met = True
            last = rule.last_triggered_at
            if last is not None and last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if last is not None and now - last < timedelta(seconds=rule.cooldown_seconds):
                continue
            rule.last_triggered_at = now
            session.add(AlertEvent(rule_id=rule.id, user_id=rule.user_id, symbol=rule.symbol,
                                   price=price, created_at=now, next_attempt_at=now))
            created += 1
        await session.commit()
    return created


async def deliver_pending(bot, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    async with SessionLocal() as session:
        events = (await session.execute(select(AlertEvent).where(
            AlertEvent.status == "pending", AlertEvent.next_attempt_at <= now
        ).order_by(AlertEvent.id).limit(20))).scalars().all()
        delivered = 0
        for event in events:
            rule = await session.get(AlertRule, event.rule_id) if event.rule_id is not None else None
            user = await session.get(User, event.user_id)
            if rule is None or user is None or not rule.enabled:
                event.status = "cancelled"
                continue
            target = threshold(rule)
            if target is None:
                event.status = "cancelled"
                continue
            direction, value = target
            message = (f"🔔 MarketPulse · {rule.name}\n{event.symbol}: цена "
                       f"{format(event.price, 'f')} {('≥' if direction == 'above' else '≤')} "
                       f"{format(value, 'f')}\nИсточник: Binance Spot · "
                       f"проверено {event.created_at:%Y-%m-%d %H:%M} UTC\n"
                       "Котировка может измениться; это не рекомендация к сделке.")
            try:
                await bot.send_message(int(user.telegram_id), message)
            except Exception as exc:
                event.attempts += 1
                event.error = type(exc).__name__[:200]
                if event.attempts >= 3:
                    event.status = "failed"
                else:
                    event.next_attempt_at = now + timedelta(seconds=30 * 2 ** (event.attempts - 1))
                logger.warning("Alert delivery failed for event %s: %s", event.id, type(exc).__name__)
            else:
                event.status = "delivered"
                event.delivered_at = datetime.now(timezone.utc)
                event.error = None
                delivered += 1
            await session.commit()
        return delivered


async def run_alerts(bot):
    provider = BinancePublicProvider()
    while True:
        try:
            await evaluate_prices(provider)
            await deliver_pending(bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Alert cycle failed")
        await asyncio.sleep(30)
