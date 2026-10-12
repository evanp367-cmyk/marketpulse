from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import urlsplit

class Settings(BaseSettings):
    app_name: str = "MarketPulse"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./marketpulse.db"
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    telegram_proxy_url: str = ""
    telegram_api_base_url: str = ""
    telegram_pro_price_stars: int = Field(default=250, ge=1, le=1000000)
    support_admin_ids: str = ""
    telegram_initdata_max_age_seconds: int = 86400
    dev_auth_enabled: bool = True
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    binance_rest_base: str = "https://data-api.binance.vision"
    binance_ws_base: str = "wss://data-stream.binance.vision/ws"
    market_stale_after_seconds: int = 30
    mini_app_url: str = ""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()


def production_config_errors(config: Settings) -> list[str]:
    """Return actionable errors for unsafe/incomplete production configuration."""
    if config.environment.strip().lower() != "production":
        return []

    errors: list[str] = []
    database_url = config.database_url.strip().lower()
    if not database_url.startswith(("postgres://", "postgresql://", "postgresql+asyncpg://")):
        errors.append("DATABASE_URL must point to PostgreSQL in production")
    if config.dev_auth_enabled:
        errors.append("DEV_AUTH_ENABLED must be false in production")
    if not config.telegram_bot_token.strip():
        errors.append("TELEGRAM_BOT_TOKEN is required in production")
    if not config.telegram_bot_username.strip():
        errors.append("TELEGRAM_BOT_USERNAME is required in production")
    if config.telegram_proxy_url.strip():
        try:
            proxy = urlsplit(config.telegram_proxy_url.strip())
            valid_proxy = proxy.scheme in {"http", "socks5"} and bool(proxy.hostname and proxy.port)
        except ValueError:
            valid_proxy = False
        if not valid_proxy:
            errors.append("TELEGRAM_PROXY_URL must be an HTTP or SOCKS5 proxy URL with host and port")
    if config.telegram_api_base_url.strip():
        try:
            api_url = urlsplit(config.telegram_api_base_url.strip())
            valid_api_url = (
                api_url.scheme == "https" and bool(api_url.hostname)
                and not api_url.username and not api_url.password
                and not api_url.query and not api_url.fragment
            )
        except ValueError:
            valid_api_url = False
        if not valid_api_url:
            errors.append("TELEGRAM_API_BASE_URL must be an HTTPS URL without credentials, query, or fragment")
    if config.telegram_api_base_url.strip() and config.telegram_proxy_url.strip():
        errors.append("Set either TELEGRAM_API_BASE_URL or TELEGRAM_PROXY_URL, not both")
    if not config.mini_app_url.strip().startswith("https://"):
        errors.append("MINI_APP_URL must be the public HTTPS frontend URL")
    origins = [origin.strip().rstrip("/") for origin in config.cors_origins.split(",") if origin.strip()]
    if not origins:
        errors.append("CORS_ORIGINS must contain the public frontend origin")
    if any(origin == "*" or not origin.startswith("https://") or "localhost" in origin or "127.0.0.1" in origin for origin in origins):
        errors.append("CORS_ORIGINS must contain only exact HTTPS production origins")
    if config.telegram_pro_price_stars > 10000:
        errors.append("TELEGRAM_PRO_PRICE_STARS cannot exceed Telegram's 10000-Star payment limit")
    if config.telegram_pro_price_stars < 1:
        errors.append("TELEGRAM_PRO_PRICE_STARS must be positive")
    return errors
