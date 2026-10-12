"""Run additive MarketPulse migrations against the configured database."""
import asyncio
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.core.config import settings
from backend.app.db.url import async_database_url
from backend.app.models.models import Base

config = context.config
target_metadata = Base.metadata


def run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    engine = create_async_engine(async_database_url(settings.database_url))
    async with engine.connect() as connection:
        await connection.run_sync(run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("MarketPulse migrations require a live database")
asyncio.run(run_async_migrations())
