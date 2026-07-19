"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from aios.database.config import DatabaseConfig, get_database_config

logger = logging.getLogger("aios.database")

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(config: DatabaseConfig | None = None) -> AsyncEngine:
    """Get or create the async engine singleton.

    Args:
        config: Optional database config. Uses global config if None.

    Returns:
        Async SQLAlchemy engine.
    """
    global _engine
    if _engine is None:
        cfg = config or get_database_config()
        _engine = create_async_engine(
            cfg.database_url,
            pool_size=cfg.pool_size,
            max_overflow=cfg.max_overflow,
            pool_timeout=cfg.pool_timeout,
            pool_recycle=cfg.pool_recycle,
            echo=cfg.echo,
        )
        logger.info("Async engine created for %s", cfg.database_url.split("@")[-1])
    return _engine


def get_session_factory(
    engine: AsyncEngine | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory.

    Args:
        engine: Optional engine. Uses singleton engine if None.

    Returns:
        Session factory for creating async sessions.
    """
    global _session_factory
    if _session_factory is None:
        eng = engine or get_engine()
        _session_factory = async_sessionmaker(
            bind=eng,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session.

    Yields:
        AsyncSession that is closed after the request.
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


async def init_engine(config: DatabaseConfig | None = None) -> AsyncEngine:
    """Initialize the database engine and verify connectivity.

    Args:
        config: Optional database config. Uses global config if None.

    Returns:
        The initialized engine.
    """
    engine = get_engine(config)

    # Verify connectivity
    try:
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        logger.info("Database connection verified")
    except Exception as exc:
        logger.error("Database connection failed: %s", exc)
        raise

    return engine


async def close_engine() -> None:
    """Close the database engine and clean up connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine closed")


async def check_database_health() -> dict[str, object]:
    """Check database health for the /health endpoint.

    Returns:
        Dictionary with database health status.
    """
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(
                __import__("sqlalchemy").text("SELECT version()")
            )
            version = result.scalar()
        return {
            "status": "healthy",
            "version": str(version),
            "pool_size": engine.pool.size(),
            "checked_in": engine.pool.checkedin(),
            "checked_out": engine.pool.checkedout(),
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "error": str(exc),
        }
