"""Auth middleware — FastAPI dependency and middleware for authentication."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from aios.auth.api_keys import APIKeyManager
from aios.auth.config import get_auth_config
from aios.auth.jwt import JWTError, JWTManager, TokenPayload
from aios.auth.models import AuthContext, UserRole

# Bearer token extractor
_bearer_scheme = HTTPBearer(auto_error=False)

# Global managers (initialized lazily)
_jwt_manager: JWTManager | None = None
_api_key_manager: APIKeyManager | None = None


def get_jwt_manager() -> JWTManager:
    """Get the global JWT manager singleton."""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager


def get_api_key_manager() -> APIKeyManager:
    """Get the global API key manager singleton."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager


def reset_auth_managers() -> None:
    """Reset global auth managers (for testing)."""
    global _jwt_manager, _api_key_manager
    _jwt_manager = None
    _api_key_manager = None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthContext:
    """FastAPI dependency to extract and validate the current user.

    Supports:
    - JWT Bearer token in Authorization header
    - API key in X-API-Key header

    Args:
        request: FastAPI request object.
        credentials: Bearer token credentials (if present).

    Returns:
        AuthContext with authenticated user info.

    Raises:
        HTTPException: If authentication fails.
    """
    config = get_auth_config()

    # If auth is disabled, return a default context
    if not config.auth_enabled:
        return AuthContext(
            user_id="anonymous",
            username="anonymous",
            email="",
            roles=(UserRole.USER,),
            auth_method="disabled",
        )

    # Try API key first (X-API-Key header)
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return await _authenticate_api_key(api_key)

    # Try JWT Bearer token
    if credentials and credentials.credentials:
        return await _authenticate_jwt(credentials.credentials)

    # No credentials provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _authenticate_jwt(token: str) -> AuthContext:
    """Authenticate via JWT token.

    Args:
        token: JWT token string.

    Returns:
        AuthContext with user info.

    Raises:
        HTTPException: If token is invalid.
    """
    try:
        jwt_manager = get_jwt_manager()
        payload = jwt_manager.validate_access_token(token)
        return AuthContext(
            user_id=payload.sub,
            username=payload.username,
            email=payload.email,
            roles=payload.roles,
            is_superuser=UserRole.ADMIN in payload.roles,
            auth_method="jwt",
            session_id=payload.jti,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def _authenticate_api_key(api_key: str) -> AuthContext:
    """Authenticate via API key.

    Args:
        api_key: API key string.

    Returns:
        AuthContext with user info.

    Raises:
        HTTPException: If API key is invalid.
    """
    api_key_manager = get_api_key_manager()
    record = api_key_manager.validate_key(api_key)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return AuthContext(
        user_id=record.user_id,
        username="",
        email="",
        roles=(UserRole.USER,),
        auth_method="api_key",
        scopes=record.scopes,
    )


def require_auth(
    allowed_roles: tuple[UserRole, ...] | None = None,
    required_scopes: tuple[str, ...] | None = None,
) -> Callable[..., Any]:
    """Create a dependency that requires specific roles or scopes.

    Args:
        allowed_roles: Tuple of allowed roles. If None, any authenticated user is allowed.
        required_scopes: Tuple of required scopes. If None, no scopes required.

    Returns:
        FastAPI dependency function.
    """

    async def _check_auth(
        auth_context: AuthContext = Depends(get_current_user),
    ) -> AuthContext:
        # Check roles
        if allowed_roles is not None:
            has_role = any(auth_context.has_role(role) for role in allowed_roles)
            if not has_role and not auth_context.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required roles: {[r.value for r in allowed_roles]}",
                )

        # Check scopes
        if required_scopes is not None:
            has_scope = any(auth_context.has_scope(scope) for scope in required_scopes)
            if not has_scope and not auth_context.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required scopes: {list(required_scopes)}",
                )

        return auth_context

    return _check_auth


# Predefined dependencies for common use cases
require_admin = require_auth(allowed_roles=(UserRole.ADMIN,))
require_user = require_auth(allowed_roles=(UserRole.USER, UserRole.ADMIN))
require_viewer = require_auth(allowed_roles=(UserRole.VIEWER, UserRole.USER, UserRole.ADMIN))
