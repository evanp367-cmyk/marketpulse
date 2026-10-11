from backend.app.db.url import async_database_url


def test_postgres_url_is_normalized_for_async_driver():
    assert async_database_url('postgres://user:pass@host/db') == 'postgresql+asyncpg://user:pass@host/db'
    assert async_database_url('postgresql://user:pass@host/db') == 'postgresql+asyncpg://user:pass@host/db'


def test_sqlite_url_is_normalized_for_async_driver():
    assert async_database_url('sqlite:///./marketpulse.db') == 'sqlite+aiosqlite:///./marketpulse.db'
    assert async_database_url('sqlite+aiosqlite:///./marketpulse.db') == 'sqlite+aiosqlite:///./marketpulse.db'
