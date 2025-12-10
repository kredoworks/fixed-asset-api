# db.py
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from config import settings
from db_base import Base  # <- import Base from separate module


# ---------- Engine & Session (async) ----------

engine = create_async_engine(
    settings.DATABASE_URL,  # e.g. postgresql+asyncpg://...
    echo=settings.DEBUG,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------- Optional init helper (for dev only) ----------

async def init_db() -> None:
    """
    Optional helper to create tables from ORM metadata.

    In production, prefer Alembic migrations.
    """
    # Import models so they are registered on Base.metadata
    import db_models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---------- FastAPI dependency ----------

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session
