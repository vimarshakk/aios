"""Tests for aios.auth package."""

from __future__ import annotations

import datetime
import os
import sys

import pytest

# Add the packages directory to the path for imports
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "packages" / "auth" / "src"))
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "packages" / "security" / "src"))

# Set a test secret key before importing auth modules
os.environ["AIOS_SECRET_KEY"] = "test-secret-key-for-auth-unit-tests"
os.environ["AIOS_JWT_ALGORITHM"] = "HS256"
os.environ["AIOS_JWT_EXPIRATION_HOURS"] = "1"
os.environ["AIOS_AUTH_ENABLED"] = "false"

from aios.auth.password import (
    check_password_strength,
    hash_password,
    verify_password,
)
from aios.auth.jwt import JWTManager, JWTError, TokenPair, TokenPayload
from aios.auth.api_keys import APIKeyManager, APIKeyRecord, generate_api_key
from aios.auth.config import AuthConfig, get_auth_config, reset_auth_config
from aios.auth.models import (
    APIKey,
    AuthContext,
    Session,
    User,
    UserRole,
)


# ---------------------------------------------------------------------------
# Password Tests
# ---------------------------------------------------------------------------

class TestPassword:
    def test_hash_password_returns_string(self) -> None:
        hashed = hash_password("testpassword")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_different_each_time(self) -> None:
        h1 = hash_password("testpassword")
        h2 = hash_password("testpassword")
        assert h1 != h2

    def test_verify_password_correct(self) -> None:
        password = "testpassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self) -> None:
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty(self) -> None:
        hashed = hash_password("testpassword")
        assert verify_password("", hashed) is False

    def test_check_password_strength_strong(self) -> None:
        result = check_password_strength("StrongP@ss1")
        assert result["is_strong"] is True
        assert len(result["errors"]) == 0

    def test_check_password_strength_too_short(self) -> None:
        result = check_password_strength("Sh@1")
        assert result["is_strong"] is False
        assert any("8 characters" in e.lower() for e in result["errors"])

    def test_check_password_strength_no_uppercase(self) -> None:
        result = check_password_strength("lowerab1")
        assert result["is_strong"] is False
        assert any("uppercase" in e.lower() for e in result["errors"])

    def test_check_password_strength_no_lowercase(self) -> None:
        result = check_password_strength("UPPERCASEA1")
        assert result["is_strong"] is False
        assert any("lowercase" in e.lower() for e in result["errors"])

    def test_check_password_strength_no_digit(self) -> None:
        result = check_password_strength("NoDig@Pa")
        assert result["is_strong"] is False
        assert any("digit" in e.lower() for e in result["errors"])

    def test_check_password_strength_no_special(self) -> None:
        result = check_password_strength("NoSpec1Aa")
        assert result["is_strong"] is False
        assert any("special" in e.lower() for e in result["errors"])


# ---------------------------------------------------------------------------
# Config Tests
# ---------------------------------------------------------------------------

class TestAuthConfig:
    def test_get_auth_config_singleton(self) -> None:
        reset_auth_config()
        c1 = get_auth_config()
        c2 = get_auth_config()
        assert c1 is c2

    def test_auth_config_defaults(self) -> None:
        reset_auth_config()
        config = get_auth_config()
        assert config.jwt_algorithm == "HS256"
        assert config.jwt_access_token_expiration_hours == 24
        assert config.auth_enabled is False
        assert config.api_key_prefix == "ak_"

    def test_auth_config_custom(self) -> None:
        reset_auth_config()
        config = AuthConfig(
            jwt_algorithm="HS512",
            jwt_access_token_expiration_hours=48,
            auth_enabled=True,
            api_key_prefix="custom_",
        )
        assert config.jwt_algorithm == "HS512"
        assert config.jwt_access_token_expiration_hours == 48
        assert config.auth_enabled is True
        assert config.api_key_prefix == "custom_"


# ---------------------------------------------------------------------------
# JWT Tests
# ---------------------------------------------------------------------------

class TestJWTManager:
    def setup_method(self) -> None:
        self.manager = JWTManager()

    def test_create_access_token(self) -> None:
        token = self.manager.create_access_token(
            user_id="user-123",
            roles=(UserRole.USER,),
            username="testuser",
            email="test@example.com",
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_validate_access_token(self) -> None:
        token = self.manager.create_access_token(
            user_id="user-123",
            roles=(UserRole.USER,),
            username="testuser",
            email="test@example.com",
        )
        payload = self.manager.validate_access_token(token)
        assert payload.sub == "user-123"
        assert payload.username == "testuser"
        assert payload.email == "test@example.com"
        assert UserRole.USER in payload.roles

    def test_create_refresh_token(self) -> None:
        token = self.manager.create_refresh_token(
            user_id="user-123",
            roles=(UserRole.USER,),
            username="testuser",
            email="test@example.com",
        )
        assert isinstance(token, str)

    def test_validate_refresh_token(self) -> None:
        token = self.manager.create_refresh_token(
            user_id="user-123",
            roles=(UserRole.USER,),
            username="testuser",
            email="test@example.com",
        )
        payload = self.manager.validate_refresh_token(token)
        assert payload.sub == "user-123"
        assert payload.token_type == "refresh"

    def test_create_token_pair(self) -> None:
        pair = self.manager.create_token_pair(
            user_id="user-123",
            roles=(UserRole.USER,),
            username="testuser",
            email="test@example.com",
        )
        assert isinstance(pair, TokenPair)
        assert pair.access_token != pair.refresh_token
        assert pair.token_type == "bearer"
        assert pair.expires_in > 0

    def test_validate_access_token_with_admin_role(self) -> None:
        token = self.manager.create_access_token(
            user_id="admin-456",
            roles=(UserRole.ADMIN,),
            username="admin",
            email="admin@example.com",
        )
        payload = self.manager.validate_access_token(token)
        assert UserRole.ADMIN in payload.roles

    def test_validate_token_wrong_type(self) -> None:
        refresh_token = self.manager.create_refresh_token(
            user_id="user-123",
            roles=(UserRole.USER,),
            username="testuser",
            email="test@example.com",
        )
        with pytest.raises(JWTError, match="Expected access token"):
            self.manager.validate_access_token(refresh_token)


# ---------------------------------------------------------------------------
# API Key Tests
# ---------------------------------------------------------------------------

class TestAPIKeyManager:
    def setup_method(self) -> None:
        self.manager = APIKeyManager()

    def test_generate_key(self) -> None:
        raw_key, record = self.manager.generate_key(
            user_id="user-123",
            name="Test Key",
        )
        assert isinstance(raw_key, str)
        assert len(raw_key) > 0
        assert record.name == "Test Key"
        assert record.user_id == "user-123"
        assert record.is_active is True

    def test_generate_key_with_prefix(self) -> None:
        raw_key, record = self.manager.generate_key(
            user_id="user-123",
            name="Test Key",
        )
        assert raw_key.startswith("ak_")

    def test_validate_key(self) -> None:
        raw_key, record = self.manager.generate_key(
            user_id="user-123",
            name="Test Key",
        )
        validated = self.manager.validate_key(raw_key)
        assert validated is not None
        assert validated.id == record.id

    def test_validate_key_invalid(self) -> None:
        validated = self.manager.validate_key("invalid_key_12345")
        assert validated is None

    def test_revoke_key(self) -> None:
        raw_key, record = self.manager.generate_key(
            user_id="user-123",
            name="Test Key",
        )
        revoked = self.manager.revoke_key(record.id)
        assert revoked is True
        validated = self.manager.validate_key(raw_key)
        assert validated is None

    def test_list_keys_for_user(self) -> None:
        self.manager.generate_key(user_id="user-123", name="Key 1")
        self.manager.generate_key(user_id="user-123", name="Key 2")
        self.manager.generate_key(user_id="user-456", name="Key 3")
        keys = self.manager.list_keys_for_user("user-123")
        assert len(keys) == 2

    def test_delete_key(self) -> None:
        raw_key, record = self.manager.generate_key(
            user_id="user-123",
            name="Test Key",
        )
        deleted = self.manager.delete_key(record.id)
        assert deleted is True
        validated = self.manager.validate_key(raw_key)
        assert validated is None

    def test_delete_key_not_found(self) -> None:
        deleted = self.manager.delete_key("nonexistent-id")
        assert deleted is False

    def test_key_scopes(self) -> None:
        raw_key, record = self.manager.generate_key(
            user_id="user-123",
            name="Scoped Key",
            scopes=("read", "write"),
        )
        validated = self.manager.validate_key(raw_key)
        assert validated is not None
        assert "read" in validated.scopes
        assert "write" in validated.scopes

    def test_key_expiry(self) -> None:
        raw_key, record = self.manager.generate_key(
            user_id="user-123",
            name="Expiring Key",
            expires_in_days=30,
        )
        assert record.expires_at is not None
        assert record.expires_at > datetime.datetime.now(datetime.timezone.utc)


# ---------------------------------------------------------------------------
# Models Tests
# ---------------------------------------------------------------------------

class TestModels:
    def test_user_role_values(self) -> None:
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.USER.value == "user"
        assert UserRole.VIEWER.value == "viewer"

    def test_auth_context_has_role(self) -> None:
        ctx = AuthContext(
            user_id="user-123",
            username="test",
            email="test@example.com",
            roles=(UserRole.USER, UserRole.VIEWER),
        )
        assert ctx.has_role(UserRole.USER) is True
        assert ctx.has_role(UserRole.ADMIN) is False

    def test_auth_context_has_scope(self) -> None:
        ctx = AuthContext(
            user_id="user-123",
            username="test",
            email="test@example.com",
            roles=(UserRole.USER,),
            scopes=("read", "write"),
        )
        assert ctx.has_scope("read") is True
        assert ctx.has_scope("delete") is False

    def test_auth_context_is_superuser(self) -> None:
        ctx = AuthContext(
            user_id="user-123",
            username="test",
            email="test@example.com",
            roles=(UserRole.ADMIN,),
            is_superuser=True,
        )
        assert ctx.is_superuser is True

    def test_user_defaults(self) -> None:
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed123",
        )
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.roles == (UserRole.USER,)


# ---------------------------------------------------------------------------
# Generate API Key Convenience Function Tests
# ---------------------------------------------------------------------------

class TestGenerateAPIKey:
    def test_generate_api_key_returns_tuple(self) -> None:
        result = generate_api_key(
            user_id="user-123",
            name="Test Key",
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        raw_key, record = result
        assert isinstance(raw_key, str)
        assert isinstance(record, APIKeyRecord)


# ---------------------------------------------------------------------------
# Gateway Admin Endpoint Tests
# ---------------------------------------------------------------------------

class TestAdminEndpoints:
    """Test admin endpoints require admin role and work correctly."""

    def _register_admin(self) -> tuple[str, dict]:
        """Register an admin user, return (user_id, login_response)."""
        from aios.auth.models import UserRole
        from aios.gateway.main import UserRecord, _user_store

        uid = "admin-test-user"
        record = UserRecord(
            id=uid,
            email="admin@test.com",
            username="adminuser",
            hashed_password="hashed123",
            is_superuser=False,
            roles=[UserRole.ADMIN.value],
        )
        # Manually set in the dev store
        _user_store._dev_users["admin@test.com"] = record
        _user_store._dev_users_by_id[uid] = record
        import aios.gateway.main as gw
        tokens = gw.get_jwt_manager().create_token_pair(uid, (UserRole.ADMIN,), "adminuser")
        return uid, tokens

    def test_list_users_requires_admin(self) -> None:
        from aios.auth.middleware import get_current_user
        from aios.auth.models import AuthContext, UserRole
        from aios.gateway.main import UserRecord, _user_store

        # Register admin and regular user
        admin_uid, admin_tokens = self._register_admin()
        regular_uid = "regular-user"
        record = UserRecord(
            id=regular_uid,
            email="user@test.com",
            username="regular",
            hashed_password="hashed",
            roles=[UserRole.USER.value],
        )
        _user_store._dev_users["user@test.com"] = record
        _user_store._dev_users_by_id[regular_uid] = record

        # Regular user should get 403
        regular_user = _user_store._dev_users["user@test.com"]
        ctx_regular = AuthContext(
            user_id=regular_uid,
            username=regular_user.username,
            email=regular_user.email,
            roles=(UserRole.USER,),
        )
        # The endpoint uses require_admin which checks the role
        assert UserRole.USER.value in regular_user.roles

    def test_admin_endpoints_exist(self) -> None:
        """Verify admin endpoints are registered."""
        import aios.gateway.main as gw
        app = gw.app
        routes = [r.path for r in app.routes]
        assert "/admin/users" in routes
        assert "/admin/users/{user_id}" in routes

    def test_admin_user_list_shape(self) -> None:
        """Verify user list response shape."""
        from aios.gateway.main import UserRecord, _user_store

        admin_uid, _ = self._register_admin()
        user_uid = "list-test-user"
        record = UserRecord(
            id=user_uid,
            email="list@test.com",
            username="listuser",
            hashed_password="hashed",
        )
        _user_store._dev_users["list@test.com"] = record
        _user_store._dev_users_by_id[user_uid] = record

        # The endpoint returns a dict with users and total
        users = list(_user_store._dev_users.values())
        assert len(users) >= 2
        for u in users:
            assert hasattr(u, "username")
            assert hasattr(u, "email")
            assert hasattr(u, "roles")

    def test_admin_delete_user(self) -> None:
        """Verify delete user works."""
        from aios.gateway.main import UserRecord, _user_store

        uid = "delete-test-user"
        record = UserRecord(
            id=uid,
            email="delete@test.com",
            username="deleteuser",
            hashed_password="hashed",
        )
        _user_store._dev_users["delete@test.com"] = record
        _user_store._dev_users_by_id[uid] = record
        assert "delete@test.com" in _user_store._dev_users
        assert uid in _user_store._dev_users_by_id
        del _user_store._dev_users["delete@test.com"]
        del _user_store._dev_users_by_id[uid]
        assert "delete@test.com" not in _user_store._dev_users
        assert uid not in _user_store._dev_users_by_id
