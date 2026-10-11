from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from backend.app.core.config import settings
from backend.app.db.url import async_database_url

engine = create_async_engine(async_database_url(settings.database_url), pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_session():
    async with SessionLocal() as session:
        yield session
