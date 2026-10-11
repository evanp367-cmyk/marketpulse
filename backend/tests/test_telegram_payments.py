from datetime import datetime, timedelta, timezone

from backend.app.telegram.payments import valid_pro_invoice, subscription_end


def test_valid_pro_invoice_requires_matching_user_price_currency_and_nonce():
    payload = "marketpulse_pro_month_123456789_0123456789abcdef0123456789abcdef"
    assert valid_pro_invoice(payload, 123456789, "XTR", 250, 250)
    assert not valid_pro_invoice(payload, 999, "XTR", 250, 250)
    assert not valid_pro_invoice(payload, 123456789, "USD", 250, 250)
    assert not valid_pro_invoice(payload, 123456789, "XTR", 498, 250)
    assert not valid_pro_invoice(payload + "x", 123456789, "XTR", 250, 250)
    assert not valid_pro_invoice("marketpulse_pro_month_dev-local-user_nonce", "dev-local-user", "XTR", 250, 250)


def test_subscription_end_extends_from_existing_future_expiry():
    now = datetime(2026, 10, 11, tzinfo=timezone.utc)
    old_end = now + timedelta(days=10)
    start, end = subscription_end(now, old_end, "pro")
    assert start == old_end
    assert end == old_end + timedelta(days=30)


def test_subscription_end_starts_now_when_existing_subscription_expired():
    now = datetime(2026, 10, 11, tzinfo=timezone.utc)
    old_end = now - timedelta(days=1)
    start, end = subscription_end(now, old_end, "pro")
    assert start == now
    assert end == now + timedelta(days=30)


def test_subscription_end_uses_telegram_expiration_when_available():
    now = datetime(2026, 10, 11, tzinfo=timezone.utc)
    expiration = int((now + timedelta(days=30)).timestamp())
    start, end = subscription_end(now, None, "free", expiration)
    assert start == now
    assert end == datetime.fromtimestamp(expiration, timezone.utc)
