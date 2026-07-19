"""JWT manager — token creation, validation, and refresh."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from aios.auth.config import get_auth_config
from aios.auth.models import UserRole


class JWTError(Exception):
    """Raised when JWT operations fail."""


class TokenPayload:
    """JWT token payload.

    Attributes:
        sub: Subject (user ID).
        jti: JWT ID for revocation.
        exp: Expiration timestamp.
        iat: Issued-at timestamp.
        type: Token type (access, refresh).
        roles: User roles.
        username: Username.
        email: Email.
    """

    def __init__(
        self,
        sub: str = "",
        jti: str = "",
        exp: datetime | None = None,
        iat: datetime | None = None,
        token_type: str = "access",
        roles: tuple[UserRole, ...] = (UserRole.USER,),
        username: str = "",
        email: str = "",
        **kwargs: Any,
    ) -> None:
        self.sub = sub
        self.jti = jti or str(uuid.uuid4())
        self.exp = exp or datetime.now(timezone.utc) + timedelta(hours=24)
        self.iat = iat or datetime.now(timezone.utc)
        self.token_type = token_type
        self.roles = roles
        self.username = username
        self.email = email
        self.extra = kwargs

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JWT encoding."""
        return {
            "sub": self.sub,
            "jti": self.jti,
            "exp": self.exp,
            "iat": self.iat,
            "type": self.token_type,
            "roles": [r.value for r in self.roles],
            "username": self.username,
            "email": self.email,
            **self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenPayload:
        """Deserialize from dict."""
        roles = tuple(UserRole(r) for r in data.get("roles", ["user"]))
        return cls(
            sub=data.get("sub", ""),
            jti=data.get("jti", ""),
            exp=data.get("exp"),
            iat=data.get("iat"),
            token_type=data.get("type", "access"),
            roles=roles,
            username=data.get("username", ""),
            email=data.get("email", ""),
        )

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        if self.exp is None:
            return False
        return datetime.now(timezone.utc) > self.exp


class TokenPair:
    """Access + refresh token pair.

    Attributes:
        access_token: JWT access token string.
        refresh_token: JWT refresh token string.
        token_type: Token type (Bearer).
        expires_in: Access token expiration in seconds.
    """

    def __init__(
        self,
        access_token: str = "",
        refresh_token: str = "",
        token_type: str = "bearer",
        expires_in: int = 86400,
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
        self.expires_in = expires_in

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for API response."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
        }


class JWTManager:
    """JWT token creation, validation, and refresh.

    Usage::

        manager = JWTManager()
        token_pair = manager.create_token_pair(user_id, roles, username, email)
        payload = manager.validate_token(token_pair.access_token)
    """

    def __init__(self, config: AuthConfig | None = None) -> None:
        self._config = config or get_auth_config()

    def create_access_token(
        self,
        user_id: str,
        roles: tuple[UserRole, ...] = (UserRole.USER,),
        username: str = "",
        email: str = "",
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """Create an access token.

        Args:
            user_id: User ID (subject).
            roles: User roles.
            username: Username.
            email: Email.
            extra_claims: Additional claims to include.

        Returns:
            Encoded JWT string.
        """
        expires = timedelta(hours=self._config.jwt_access_token_expiration_hours)
        payload = TokenPayload(
            sub=user_id,
            exp=datetime.now(timezone.utc) + expires,
            token_type="access",
            roles=roles,
            username=username,
            email=email,
            **(extra_claims or {}),
        )
        return self._encode(payload.to_dict())

    def create_refresh_token(
        self,
        user_id: str,
        roles: tuple[UserRole, ...] = (UserRole.USER,),
        username: str = "",
        email: str = "",
    ) -> str:
        """Create a refresh token.

        Args:
            user_id: User ID (subject).
            roles: User roles.
            username: Username.
            email: Email.

        Returns:
            Encoded JWT string.
        """
        expires = timedelta(days=self._config.jwt_refresh_token_expiration_days)
        payload = TokenPayload(
            sub=user_id,
            exp=datetime.now(timezone.utc) + expires,
            token_type="refresh",
            roles=roles,
            username=username,
            email=email,
        )
        return self._encode(payload.to_dict())

    def create_token_pair(
        self,
        user_id: str,
        roles: tuple[UserRole, ...] = (UserRole.USER,),
        username: str = "",
        email: str = "",
    ) -> TokenPair:
        """Create an access + refresh token pair.

        Args:
            user_id: User ID (subject).
            roles: User roles.
            username: Username.
            email: Email.

        Returns:
            TokenPair with both tokens.
        """
        access_token = self.create_access_token(user_id, roles, username, email)
        refresh_token = self.create_refresh_token(user_id, roles, username, email)
        expires_in = self._config.jwt_access_token_expiration_hours * 3600
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

    def validate_token(self, token: str) -> TokenPayload:
        """Validate and decode a JWT token.

        Args:
            token: Encoded JWT string.

        Returns:
            Decoded TokenPayload.

        Raises:
            JWTError: If token is invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                self._config.jwt_secret_key,
                algorithms=[self._config.jwt_algorithm],
            )
            return TokenPayload.from_dict(payload)
        except JWTError as exc:
            raise JWTError(f"Invalid token: {exc}") from exc

    def validate_access_token(self, token: str) -> TokenPayload:
        """Validate an access token specifically.

        Args:
            token: Encoded JWT string.

        Returns:
            Decoded TokenPayload.

        Raises:
            JWTError: If token is invalid, expired, or not an access token.
        """
        payload = self.validate_token(token)
        if payload.token_type != "access":
            raise JWTError(f"Expected access token, got {payload.token_type}")
        return payload

    def validate_refresh_token(self, token: str) -> TokenPayload:
        """Validate a refresh token specifically.

        Args:
            token: Encoded JWT string.

        Returns:
            Decoded TokenPayload.

        Raises:
            JWTError: If token is invalid, expired, or not a refresh token.
        """
        payload = self.validate_token(token)
        if payload.token_type != "refresh":
            raise JWTError(f"Expected refresh token, got {payload.token_type}")
        return payload

    def _encode(self, payload: dict[str, Any]) -> str:
        """Encode a payload to JWT string."""
        return jwt.encode(
            payload,
            self._config.jwt_secret_key,
            algorithm=self._config.jwt_algorithm,
        )
