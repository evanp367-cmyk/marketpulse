import asyncio
from datetime import datetime, timezone
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, PreCheckoutQuery
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.models.models import User, Subscription, Payment
from backend.app.telegram.payments import valid_pro_invoice, subscription_end

async def main():
    if not settings.telegram_bot_token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN in .env before starting the bot")
    if settings.telegram_pro_price_stars < 1:
        raise RuntimeError("TELEGRAM_PRO_PRICE_STARS must be a positive integer")
    bot = Bot(settings.telegram_bot_token)
    dp = Dispatcher()
    support_waiting: set[int] = set()

    @dp.message(CommandStart())
    async def start(message: Message):
        text = (f"{settings.app_name}: крипторынок и аналитика.\n\n"
                "Рыночные данные могут быть недоступны при проблемах у поставщика. "
                "Сигналы — это технические индикаторы, а не персональные рекомендации и не гарантия прибыли.")
        if settings.mini_app_url.startswith("https://"):
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть терминал", web_app=WebAppInfo(url=settings.mini_app_url))]])
            await message.answer(text, reply_markup=kb)
        else:
            await message.answer(text + "\n\nMini App пока не настроен: укажите MINI_APP_URL (HTTPS).")

    @dp.pre_checkout_query()
    async def pre_checkout(query: PreCheckoutQuery):
        valid = valid_pro_invoice(
            query.invoice_payload, query.from_user.id, query.currency,
            query.total_amount, settings.telegram_pro_price_stars,
        )
        if valid:
            await query.answer(ok=True)
        else:
            await query.answer(ok=False, error_message="This MarketPulse payment could not be verified.")

    @dp.message(F.successful_payment)
    async def successful_payment(message: Message):
        payment = message.successful_payment
        telegram_id = str(message.from_user.id) if message.from_user else ""
        charge_id = payment.telegram_payment_charge_id
        if not telegram_id or not charge_id or not valid_pro_invoice(
            payment.invoice_payload, telegram_id, payment.currency,
            payment.total_amount, settings.telegram_pro_price_stars,
        ):
            await message.answer("Платёж получен, но его параметры не совпали с тарифом MarketPulse Pro. Напишите в поддержку через /paysupport.")
            return
        async with SessionLocal() as session:
            duplicate = await session.scalar(select(Payment).where(Payment.provider_payment_id == charge_id))
            if duplicate:
                await message.answer("Этот платёж уже учтён. Статус подписки можно проверить в разделе тарифов MarketPulse.")
                return
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                user = User(telegram_id=telegram_id)
                session.add(user)
                await session.flush()
            now = datetime.now(timezone.utc)
            sub = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
            previous_end = sub.ends_at if sub else None
            previous_plan = sub.plan_code if sub else "free"
            telegram_expiry = getattr(payment, "subscription_expiration_date", None)
            starts_at, ends_at = subscription_end(now, previous_end, previous_plan, telegram_expiry)
            if sub is None:
                sub = Subscription(user_id=user.id, plan_code="pro", status="active", provider="telegram_stars", starts_at=starts_at, ends_at=ends_at)
                session.add(sub)
            else:
                sub.plan_code = "pro"
                sub.status = "active"
                sub.provider = "telegram_stars"
                sub.starts_at = starts_at
                sub.ends_at = ends_at
            session.add(Payment(user_id=user.id, provider_payment_id=charge_id, amount=payment.total_amount, currency=payment.currency, status="successful"))
            try:
                await session.commit()
            except IntegrityError:
                # Concurrent duplicate Telegram updates must not grant time twice.
                await session.rollback()
                duplicate = await session.scalar(select(Payment).where(Payment.provider_payment_id == charge_id))
                if duplicate:
                    await message.answer("Этот платёж уже учтён. Статус подписки можно проверить в разделе тарифов MarketPulse.")
                    return
                raise
        await message.answer("Оплата подтверждена! MarketPulse Pro активирован. Откройте Mini App заново, чтобы обновить тариф.")

    @dp.message(Command("terms"))
    async def terms(message: Message):
        await message.answer(
            "Условия MarketPulse Pro: подписка открывает перечисленные в разделе тарифов цифровые функции на период, указанный при оплате. "
            "Котировки могут задерживаться или быть недоступны; аналитика и сигналы не являются индивидуальной инвестиционной рекомендацией и не гарантируют прибыль. "
            "Платежи внутри Telegram выполняются в Stars. Для вопросов по платежу, отмене или возврату используйте /paysupport. "
            "Новая оплата предоставляет 30 дней Pro без автоматического продления. Доступ прекращается после окончания оплаченного периода; следующую оплату пользователь оформляет самостоятельно."
        )

    @dp.message(Command("paysupport"))
    async def pay_support(message: Message):
        if not message.from_user:
            return
        support_waiting.add(message.from_user.id)
        await message.answer(
            "Поддержка по оплатам MarketPulse. Отправьте одним сообщением дату платежа, сумму в Stars и ID транзакции, если он доступен. "
            "Не отправляйте пароли, токены бота или коды входа.\n"
            f"Ваш Telegram ID: {message.from_user.id}"
        )

    @dp.message(F.text)
    async def forward_payment_support(message: Message):
        if not message.from_user or message.from_user.id not in support_waiting or not message.text:
            return
        support_waiting.discard(message.from_user.id)
        admin_ids = []
        for raw_id in settings.support_admin_ids.split(","):
            raw_id = raw_id.strip()
            if raw_id.isdigit():
                admin_ids.append(int(raw_id))
        if not admin_ids:
            await message.answer("Обращение не отправлено: поддержка ещё не настроена. Владелец MarketPulse должен указать свой Telegram ID в SUPPORT_ADMIN_IDS в файле .env.")
            return
        forwarded = 0
        for admin_id in set(admin_ids):
            try:
                await bot.send_message(
                    admin_id,
                    "Обращение по оплате MarketPulse\n"
                    f"Telegram ID пользователя: {message.from_user.id}\n"
                    f"Username: @{message.from_user.username or 'не указан'}\n"
                    f"Сообщение: {message.text[:3000]}"
                )
                forwarded += 1
            except Exception:
                continue
        if forwarded:
            await message.answer("Обращение передано поддержке MarketPulse. Не отправляйте пароли или коды подтверждения.")
        else:
            await message.answer("Не удалось доставить обращение поддержке. Попробуйте позже или свяжитесь с владельцем MarketPulse другим способом.")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
