"""Database configuration — async database URL and pool settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    """Async database configuration.

    All settings can be overridden via environment variables with AIOS_ prefix.
    """

    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/aios",
        )
    )
    pool_size: int = field(
        default_factory=lambda: int(os.getenv("AIOS_DB_POOL_SIZE", "10"))
    )
    max_overflow: int = field(
        default_factory=lambda: int(os.getenv("AIOS_DB_MAX_OVERFLOW", "20"))
    )
    pool_timeout: int = field(
        default_factory=lambda: int(os.getenv("AIOS_DB_POOL_TIMEOUT", "30"))
    )
    pool_recycle: int = field(
        default_factory=lambda: int(os.getenv("AIOS_DB_POOL_RECYCLE", "3600"))
    )
    echo: bool = field(
        default_factory=lambda: os.getenv("AIOS_DB_ECHO", "false").lower() == "true"
    )


_db_config: DatabaseConfig | None = None


def get_database_config() -> DatabaseConfig:
    """Get the global database config singleton."""
    global _db_config
    if _db_config is None:
        _db_config = DatabaseConfig()
    return _db_config


def reset_database_config() -> None:
    """Reset the global database config (for testing)."""
    global _db_config
    _db_config = None
