"""SQLAlchemy ORM models — Base and domain models.

Uses dialect-conditional types so tests can run against SQLite while
production uses PostgreSQL features (JSONB, ARRAY, native UUID).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.types import JSON, TypeDecorator


# ---------------------------------------------------------------------------
# Portable type helpers
# ---------------------------------------------------------------------------

class _PortableJSON(TypeDecorator):
    """JSON that degrades to plain JSON type on non-PostgreSQL dialects."""
    impl = JSON
    cache_ok = True


def _jsonb_col(*, default=None, nullable=False):
    """Return a Column using JSONB on Postgres, JSON elsewhere."""
    from sqlalchemy import inspect as sa_inspect
    # We'll use a simple approach: always use JSON (which works everywhere).
    # On PostgreSQL, we can migrate to JSONB later via Alembic.
    default = default if default is not None else {}
    return Column(JSON, default=default, nullable=nullable)


class _PortableUUID(TypeDecorator):
    """UUID type: native UUID on PostgreSQL, CHAR(36) on others."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value)
        return value


def _uuid_pk():
    """UUID primary key column — native on PG, CHAR(36) elsewhere."""
    return Column(_PortableUUID, primary_key=True, default=lambda: str(uuid.uuid4()))


def _uuid_fk(target: str, *, ondelete: str = "CASCADE", nullable: bool = False):
    """UUID foreign key column."""
    return Column(_PortableUUID, ForeignKey(target, ondelete=ondelete), nullable=nullable)


def _uuid_col(*, nullable: bool = True, index: bool = False):
    """UUID column (not PK/FK)."""
    kw: dict = {"nullable": nullable}
    if index:
        kw["index"] = True
    return Column(_PortableUUID, **kw)


class _StringArray(TypeDecorator):
    """Portable string array: JSON array on all dialects."""
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return list(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return list(value)
        return value


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Auth Models
# ---------------------------------------------------------------------------


class UserModel(Base):
    """User account for authentication."""

    __tablename__ = "users"

    id = _uuid_pk()
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    roles = Column(_StringArray, default=["user"], nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    api_keys = relationship("APIKeyModel", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class APIKeyModel(Base):
    """API key for programmatic access."""

    __tablename__ = "api_keys"

    id = _uuid_pk()
    user_id = _uuid_fk("users.id")
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(15), nullable=False)
    scopes = Column(_StringArray, default=[], nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("UserModel", back_populates="api_keys")

    __table_args__ = (
        Index("ix_api_keys_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<APIKey id={self.id} name={self.name}>"


class SessionModel(Base):
    """User session for token tracking."""

    __tablename__ = "sessions"

    id = _uuid_pk()
    user_id = _uuid_fk("users.id")
    token_jti = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("UserModel", back_populates="sessions")

    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id} user_id={self.user_id}>"


# ---------------------------------------------------------------------------
# Memory Models
# ---------------------------------------------------------------------------


class MemoryModel(Base):
    """Long-term memory entries."""

    __tablename__ = "memories"

    id = _uuid_pk()
    user_id = _uuid_fk("users.id", nullable=True)
    content = Column(Text, nullable=False)
    memory_type = Column(String(50), nullable=False, default="episodic")
    metadata_json = _jsonb_col(default={})
    embedding = Column(Text, nullable=True)  # JSON-serialized vector
    importance = Column(Float, default=0.5, nullable=False)
    access_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_accessed = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_memories_user_id", "user_id"),
        Index("ix_memories_memory_type", "memory_type"),
        Index("ix_memories_importance", "importance"),
    )

    def __repr__(self) -> str:
        return f"<Memory id={self.id} type={self.memory_type}>"


# ---------------------------------------------------------------------------
# Goal Models
# ---------------------------------------------------------------------------


class GoalModel(Base):
    """Agent goals for planning and tracking."""

    __tablename__ = "goals"

    id = _uuid_pk()
    user_id = _uuid_fk("users.id", nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    priority = Column(Integer, default=0, nullable=False)
    progress = Column(Float, default=0.0, nullable=False)
    metadata_json = _jsonb_col(default={})
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_goals_user_id", "user_id"),
        Index("ix_goals_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Goal id={self.id} title={self.title[:50]}>"


# ---------------------------------------------------------------------------
# Audit Log Model
# ---------------------------------------------------------------------------


class AuditLogModel(Base):
    """Security audit trail for all sensitive operations."""

    __tablename__ = "audit_logs"

    id = _uuid_pk()
    user_id = _uuid_col(nullable=True)
    action = Column(String(255), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(255), nullable=True)
    details = _jsonb_col(default={})
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="success")
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action}>"
