"""API key management — generation, validation, and hashing."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from aios.auth.config import get_auth_config


class APIKeyError(Exception):
    """Raised when API key operations fail."""


@dataclass(frozen=True, slots=True)
class APIKeyRecord:
    """In-memory API key record for testing.

    In production, this would be stored in the database.
    """

    id: str
    user_id: str
    name: str
    key_hash: str
    key_prefix: str
    scopes: tuple[str, ...]
    is_active: bool
    expires_at: datetime | None
    created_at: datetime
    last_used_at: datetime | None

    @property
    def is_expired(self) -> bool:
        """Check if the key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the key is valid (active and not expired)."""
        return self.is_active and not self.is_expired

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict (excludes sensitive fields)."""
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


class APIKeyManager:
    """API key generation, validation, and management.

    Usage::

        manager = APIKeyManager()
        key, record = manager.generate_key(user_id="user123", name="my-key")
        # key is the raw API key (shown once)
        # record is the stored record (with hash)
        is_valid = manager.validate_key(key, record)
    """

    def __init__(self, config: Any | None = None) -> None:
        self._config = config or get_auth_config()
        self._keys: dict[str, APIKeyRecord] = {}  # key_hash -> record

    def generate_key(
        self,
        user_id: str,
        name: str,
        scopes: tuple[str, ...] = (),
        expires_in_days: int | None = None,
    ) -> tuple[str, APIKeyRecord]:
        """Generate a new API key.

        Args:
            user_id: Owner user ID.
            name: Human-readable key name.
            scopes: Allowed scopes/permissions.
            expires_in_days: Optional expiration in days.

        Returns:
            Tuple of (raw_key, key_record).
        """
        # Generate random key
        raw_key = secrets.token_urlsafe(self._config.api_key_length)
        key_with_prefix = f"{self._config.api_key_prefix}{raw_key}"

        # Hash the key for storage
        key_hash = self._hash_key(key_with_prefix)
        key_prefix = key_with_prefix[:10]

        # Calculate expiration
        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        # Create record
        record = APIKeyRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=scopes,
            is_active=True,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
            last_used_at=None,
        )

        # Store the record
        self._keys[key_hash] = record

        return key_with_prefix, record

    def validate_key(self, raw_key: str) -> APIKeyRecord | None:
        """Validate an API key and return its record.

        Args:
            raw_key: The raw API key to validate.

        Returns:
            APIKeyRecord if valid, None otherwise.
        """
        key_hash = self._hash_key(raw_key)
        record = self._keys.get(key_hash)

        if record is None:
            return None

        if not record.is_valid:
            return None

        # Update last used timestamp (frozen dataclass — use object.__setattr__)
        updated = APIKeyRecord(
            id=record.id,
            user_id=record.user_id,
            name=record.name,
            key_hash=record.key_hash,
            key_prefix=record.key_prefix,
            scopes=record.scopes,
            is_active=record.is_active,
            expires_at=record.expires_at,
            created_at=record.created_at,
            last_used_at=datetime.now(timezone.utc),
        )
        self._keys[key_hash] = updated
        return updated

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key by ID.

        Args:
            key_id: The key ID to revoke.

        Returns:
            True if the key was revoked, False if not found.
        """
        for record in self._keys.values():
            if record.id == key_id:
                # Create a new record with is_active=False
                revoked = APIKeyRecord(
                    id=record.id,
                    user_id=record.user_id,
                    name=record.name,
                    key_hash=record.key_hash,
                    key_prefix=record.key_prefix,
                    scopes=record.scopes,
                    is_active=False,
                    expires_at=record.expires_at,
                    created_at=record.created_at,
                    last_used_at=record.last_used_at,
                )
                self._keys[record.key_hash] = revoked
                return True
        return False

    def list_keys_for_user(self, user_id: str) -> list[APIKeyRecord]:
        """List all API keys for a user.

        Args:
            user_id: User ID to list keys for.

        Returns:
            List of APIKeyRecord instances.
        """
        return [
            record for record in self._keys.values()
            if record.user_id == user_id
        ]

    def delete_key(self, key_id: str) -> bool:
        """Permanently delete an API key by ID.

        Args:
            key_id: The key ID to delete.

        Returns:
            True if the key was deleted, False if not found.
        """
        for key_hash, record in self._keys.items():
            if record.id == key_id:
                del self._keys[key_hash]
                return True
        return False

    @staticmethod
    def _hash_key(key: str) -> str:
        """Hash an API key using SHA-256.

        Args:
            key: Raw API key.

        Returns:
            SHA-256 hash string.
        """
        return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key(
    user_id: str,
    name: str,
    scopes: tuple[str, ...] = (),
    expires_in_days: int | None = None,
) -> tuple[str, APIKeyRecord]:
    """Convenience function to generate an API key.

    Args:
        user_id: Owner user ID.
        name: Human-readable key name.
        scopes: Allowed scopes/permissions.
        expires_in_days: Optional expiration in days.

    Returns:
        Tuple of (raw_key, key_record).
    """
    manager = APIKeyManager()
    return manager.generate_key(user_id, name, scopes, expires_in_days)
