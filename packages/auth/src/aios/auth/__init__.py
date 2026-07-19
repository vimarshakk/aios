"""AIOS Authentication & Identity — JWT, API keys, password hashing."""

from __future__ import annotations

from aios.auth.api_keys import APIKeyManager, APIKeyRecord, generate_api_key
from aios.auth.config import AuthConfig, get_auth_config
from aios.auth.jwt import JWTManager, TokenPair, TokenPayload
from aios.auth.middleware import AuthContext, get_current_user, require_auth
from aios.auth.models import APIKey, Session, User
from aios.auth.password import hash_password, verify_password

API_VERSION = "1.0"

__all__ = [
    "API_KEY_PREFIX",
    "APIKey",
    "APIKeyManager",
    "APIKeyRecord",
    "AuthConfig",
    "AuthContext",
    "JWTManager",
    "Session",
    "TokenPair",
    "TokenPayload",
    "User",
    "generate_api_key",
    "get_auth_config",
    "get_current_user",
    "hash_password",
    "require_auth",
    "verify_password",
]

API_KEY_PREFIX = "ak_"
