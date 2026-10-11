import hashlib, hmac, json, time
from urllib.parse import parse_qsl
from fastapi import Header, HTTPException
from backend.app.core.config import settings

def validate_telegram_init_data(init_data: str, bot_token: str, max_age_seconds: int) -> dict:
    if not init_data or not bot_token: raise ValueError("Missing initData or bot token")
    parsed_pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    keys = [key for key, _ in parsed_pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate Telegram initData fields")
    pairs = dict(parsed_pairs)
    received_hash=pairs.pop("hash", None)
    if not received_hash: raise ValueError("Missing Telegram hash")
    check_string="\n".join(f"{k}={v}" for k,v in sorted(pairs.items()))
    secret=hmac.new(b"WebAppData",bot_token.encode(),hashlib.sha256).digest()
    expected=hmac.new(secret,check_string.encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,received_hash): raise ValueError("Invalid Telegram signature")
    auth_date=int(pairs.get("auth_date","0"))
    now=int(time.time())
    if auth_date>now+60 or now-auth_date>max_age_seconds: raise ValueError("Telegram initData expired or from future")
    user=json.loads(pairs.get("user","{}"))
    if not isinstance(user,dict): raise ValueError("Telegram user missing")
    user_id = user.get("id")
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("Telegram user ID is invalid")
    return user

async def current_user(x_telegram_init_data: str | None = Header(default=None), x_dev_user: str | None = Header(default=None)):
    from backend.app.db.session import SessionLocal
    from backend.app.models.models import User
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError
    if settings.environment == "development" and settings.dev_auth_enabled and x_dev_user == "local-dev":
        telegram_id="dev-local-user"
    else:
        try:
            if not settings.telegram_bot_token: raise ValueError("Bot token is not configured")
            data=validate_telegram_init_data(x_telegram_init_data or "",settings.telegram_bot_token,settings.telegram_initdata_max_age_seconds)
            telegram_id=str(data["id"])
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=401,detail="Valid Telegram Mini App authorization is required") from exc
    async with SessionLocal() as session:
        result=await session.execute(select(User).where(User.telegram_id==telegram_id)); user=result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id)
            session.add(user)
            try:
                await session.commit()
            except IntegrityError:
                # Parallel first requests may create the same Telegram user.
                await session.rollback()
                user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
                if user is None:
                    raise
            else:
                await session.refresh(user)
        # Detach for safe use after session closes; fields needed by routes are scalar.
        return user
