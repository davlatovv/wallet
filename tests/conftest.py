import os

os.environ.setdefault("BOT_TOKEN", "123456:TEST-TOKEN")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-with-enough-length-for-hs256!")


import pytest  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402


@pytest.fixture
async def session():
    """Real SQLAlchemy session on in-memory SQLite (users 1 and 2 pre-created).
    `FOR UPDATE` is a no-op on SQLite, so row locking is not covered by tests using this."""
    from app.infrastructure.db.models.base import Base
    from app.infrastructure.db.models import category, reminder, transaction, user  # noqa: F401
    from app.infrastructure.db.models.user import User

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        s.add_all([User(id=1), User(id=2)])
        await s.flush()
        yield s
    await engine.dispose()
