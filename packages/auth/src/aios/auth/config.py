"""Auth configuration — JWT and API key settings via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class AuthConfig(BaseSettings):
    """Authentication configuration.

    All settings can be overridden via environment variables with AIOS_ prefix.
    """

    model_config = {"env_prefix": "AIOS_", "env_file": ".env", "extra": "ignore"}

    # JWT settings
    jwt_secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expiration_hours: int = 24
    jwt_refresh_token_expiration_days: int = 30

    # API key settings
    api_key_prefix: str = "ak_"
    api_key_length: int = 32
    api_key_max_per_user: int = 10

    # Password settings
    password_min_length: int = 8
    password_max_length: int = 128

    # Rate limiting for auth endpoints
    auth_rate_limit_per_minute: int = 10
    login_rate_limit_per_minute: int = 5

    # Auth enabled flag
    auth_enabled: bool = False


_auth_config: AuthConfig | None = None


def get_auth_config() -> AuthConfig:
    """Get the global auth configuration singleton."""
    global _auth_config
    if _auth_config is None:
        _auth_config = AuthConfig()
    return _auth_config


def reset_auth_config() -> None:
    """Reset the global auth configuration (for testing)."""
    global _auth_config
    _auth_config = None
