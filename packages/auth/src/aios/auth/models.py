"""Auth models — User, APIKey, Session, and AuthContext data models."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class UserRole(StrEnum):
    """User roles for RBAC."""

    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


@dataclass(frozen=True, slots=True)
class User:
    """User model for authentication.

    Attributes:
        id: Unique user identifier (UUID).
        email: User email address.
        username: Unique username.
        hashed_password: Bcrypt-hashed password.
        is_active: Whether the user account is active.
        is_superuser: Whether the user has superuser privileges.
        roles: User roles for RBAC.
        created_at: Account creation timestamp.
        updated_at: Last update timestamp.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str = ""
    username: str = ""
    hashed_password: str = ""
    is_active: bool = True
    is_superuser: bool = False
    roles: tuple[UserRole, ...] = (UserRole.USER,)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def role(self) -> UserRole:
        """Primary role — first role in the tuple."""
        return self.roles[0] if self.roles else UserRole.USER

    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role."""
        return role in self.roles or self.is_superuser

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict (excludes sensitive fields)."""
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "roles": [r.value for r in self.roles],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class APIKey:
    """API key model for programmatic access.

    Attributes:
        id: Unique key identifier (UUID).
        user_id: Owner user ID.
        name: Human-readable key name.
        key_hash: SHA-256 hash of the actual key.
        key_prefix: First 10 chars for identification.
        scopes: Allowed scopes/permissions.
        is_active: Whether the key is active.
        expires_at: Optional expiration timestamp.
        created_at: Key creation timestamp.
        last_used_at: Last usage timestamp.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: str = ""
    key_hash: str = ""
    key_prefix: str = ""
    scopes: tuple[str, ...] = ()
    is_active: bool = True
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: datetime | None = None

    @property
    def is_expired(self) -> bool:
        """Check if the key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict (excludes sensitive fields)."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "key_prefix": self.key_prefix,
            "scopes": list(self.scopes),
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }


@dataclass(frozen=True, slots=True)
class Session:
    """Session model for token tracking.

    Attributes:
        id: Unique session identifier (UUID).
        user_id: Owner user ID.
        token_jti: JWT ID for revocation.
        expires_at: Token expiration timestamp.
        created_at: Session creation timestamp.
        revoked_at: Revocation timestamp (None if active).
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    token_jti: str = ""
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    revoked_at: datetime | None = None

    @property
    def is_revoked(self) -> bool:
        """Check if the session has been revoked."""
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the session is valid (not revoked and not expired)."""
        return not self.is_revoked and not self.is_expired


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Authentication context passed to endpoint handlers.

    Attributes:
        user_id: Authenticated user ID.
        username: Authenticated username.
        email: Authenticated email.
        roles: User roles.
        is_superuser: Whether user is superuser.
        auth_method: How the user authenticated (jwt, api_key).
        scopes: Allowed scopes (for API keys).
        session_id: Session ID (for JWT auth).
    """

    user_id: str = ""
    username: str = ""
    email: str = ""
    roles: tuple[UserRole, ...] = (UserRole.USER,)
    is_superuser: bool = False
    auth_method: str = "jwt"
    scopes: tuple[str, ...] = ()
    session_id: str = ""

    def has_role(self, role: UserRole) -> bool:
        """Check if context has a specific role."""
        return role in self.roles or self.is_superuser

    def has_scope(self, scope: str) -> bool:
        """Check if context has a specific scope."""
        if self.is_superuser:
            return True
        return scope in self.scopes or "admin" in self.scopes

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "roles": [r.value for r in self.roles],
            "is_superuser": self.is_superuser,
            "auth_method": self.auth_method,
            "scopes": list(self.scopes),
            "session_id": self.session_id,
        }
