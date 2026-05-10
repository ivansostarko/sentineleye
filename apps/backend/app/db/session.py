"""Async SQLAlchemy engine + session factory."""

from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
log = get_logger(__name__)

_engine = create_async_engine(
    str(settings.database_url),
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

_SessionLocal = async_sessionmaker(
    _engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a transactional session."""
    async with _SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def ping_database() -> None:
    """Used by health checks; raises if the DB is not reachable."""
    async with _engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def close_engine() -> None:
    await _engine.dispose()
    log.info("database.engine.closed")
