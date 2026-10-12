from backend.app.core.config import Settings, production_config_errors


def production_settings(**overrides):
    values = {
        "environment": "production",
        "database_url": "postgresql+asyncpg://user:pass@db.example.com:5432/marketpulse",
        "telegram_bot_token": "123456:secret",
        "telegram_bot_username": "marketpulse_bot",
        "telegram_pro_price_stars": 250,
        "support_admin_ids": "12345",
        "telegram_initdata_max_age_seconds": 86400,
        "dev_auth_enabled": False,
        "cors_origins": "https://marketpulse-frontend.onrender.com",
        "mini_app_url": "https://marketpulse-frontend.onrender.com",
    }
    values.update(overrides)
    return Settings(**values)


def test_valid_production_configuration_has_no_errors():
    assert production_config_errors(production_settings()) == []


def test_production_blocks_sqlite_dev_auth_and_missing_bot_token():
    errors = production_config_errors(production_settings(
        database_url="sqlite+aiosqlite:///./marketpulse.db",
        dev_auth_enabled=True,
        telegram_bot_token="",
    ))
    assert any("DATABASE_URL" in error for error in errors)
    assert any("DEV_AUTH_ENABLED" in error for error in errors)
    assert any("TELEGRAM_BOT_TOKEN" in error for error in errors)


def test_production_requires_https_and_exact_origins():
    errors = production_config_errors(production_settings(
        mini_app_url="http://localhost:5173",
        cors_origins="*,http://localhost:5173",
    ))
    assert any("MINI_APP_URL" in error for error in errors)
    assert any("CORS_ORIGINS" in error for error in errors)


def test_production_obeys_telegram_star_limit():
    errors = production_config_errors(production_settings(telegram_pro_price_stars=10001))
    assert any("10000-Star" in error for error in errors)


def test_production_accepts_socks_proxy_and_rejects_malformed_proxy():
    assert production_config_errors(production_settings(
        telegram_proxy_url="socks5://user:pass@proxy.example:1080",
    )) == []
    errors = production_config_errors(production_settings(
        telegram_proxy_url="socks5://proxy.example:not-a-port",
    ))
    assert any("TELEGRAM_PROXY_URL" in error for error in errors)


def test_production_guard_is_not_applied_to_local_development():
    local = Settings(environment="development", database_url="sqlite+aiosqlite:///./marketpulse.db")
    assert production_config_errors(local) == []
