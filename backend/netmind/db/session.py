"""
SQLAlchemy async engine and session factory.

Design decisions:
- async engine via asyncpg: required for FastAPI's async request handlers
- scoped session per request via dependency injection (see api/dependencies.py)
- pool_pre_ping=True: detects stale connections (important for long-running containers)
- echo=False in production: SQL logging only in development
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from netmind.core.config import get_postgres_settings, get_settings
from netmind.core.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """
    Declarative base for all SQLAlchemy ORM models.

    All model classes inherit from this. Alembic autogenerate reads metadata
    from Base.metadata to detect schema changes.
    """

    pass


def get_engine() -> AsyncEngine:
    """
    Return the singleton async database engine.

    Raises RuntimeError if the engine has not been initialized.
    Call create_engine_from_settings() during application startup.
    """
    if _engine is None:
        raise RuntimeError(
            "Database engine not initialized. "
            "Ensure init_db() is called during application startup."
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the singleton session factory."""
    if _session_factory is None:
        raise RuntimeError("Session factory not initialized.")
    return _session_factory


def create_engine_from_settings() -> AsyncEngine:
    """
    Create and configure the async SQLAlchemy engine.

    Called once during application startup.
    """
    settings = get_settings()
    pg_settings = get_postgres_settings()

    engine = create_async_engine(
        pg_settings.async_dsn,
        echo=settings.is_development,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,  # Recycle connections every 30 minutes
        json_serializer=_json_serializer,
        json_deserializer=_json_deserializer,
    )

    logger.info(
        "Database engine created",
        host=pg_settings.host,
        port=pg_settings.port,
        database=pg_settings.db,
    )

    return engine


def _json_serializer(value: Any) -> str:
    """Use orjson for faster JSON serialization."""
    import orjson

    return orjson.dumps(value).decode()


def _json_deserializer(value: str) -> Any:
    """Use orjson for faster JSON deserialization."""
    import orjson

    return orjson.loads(value)


async def init_db() -> None:
    """
    Initialize database engine and session factory.

    Must be called during FastAPI startup event.
    """
    global _engine, _session_factory  # noqa: PLW0603

    _engine = create_engine_from_settings()
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    logger.info("Database session factory initialized")


async def close_db() -> None:
    """
    Dispose the engine and release all connections.

    Called during FastAPI shutdown event.
    """
    global _engine, _session_factory  # noqa: PLW0603

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.

    Commits on success, rolls back on any exception.
    Session is always closed after the request completes.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
