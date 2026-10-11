"""Database URL normalization helpers for async SQLAlchemy drivers."""


def async_database_url(url: str) -> str:
    """Normalize common deployment DATABASE_URL schemes for SQLAlchemy asyncio."""
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    if url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
        return "sqlite+aiosqlite://" + url[len("sqlite://"):]
    return url
