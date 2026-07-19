"""Tests for aios.database package — uses SQLite for testing."""

from __future__ import annotations

import asyncio
import os
import sys

import pytest

# Set up test environment
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_aios.db"
os.environ["AIOS_DB_ECHO"] = "false"

# Add packages to path
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "packages" / "database" / "src"))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from aios.database.models import (
    Base,
    UserModel,
    APIKeyModel,
    MemoryModel,
    GoalModel,
    AuditLogModel,
    SessionModel,
)
from aios.database.repositories import (
    UserRepository,
    APIKeyRepository,
    MemoryRepository,
    GoalRepository,
    AuditLogRepository,
    SessionRepository,
)
from aios.database.config import DatabaseConfig, get_database_config, reset_database_config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_config() -> DatabaseConfig:
    """Create a test database config."""
    reset_database_config()
    return DatabaseConfig(
        database_url="sqlite+aiosqlite://",
        pool_size=5,
        max_overflow=5,
        echo=False,
    )


@pytest.fixture
async def engine(db_config: DatabaseConfig):
    """Create a test engine."""
    eng = create_async_engine(
        db_config.database_url,
        echo=False,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def session(engine) -> AsyncSession:
    """Create a test session."""
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


# ---------------------------------------------------------------------------
# Config Tests
# ---------------------------------------------------------------------------

class TestDatabaseConfig:
    def test_config_defaults(self) -> None:
        reset_database_config()
        config = get_database_config()
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600

    def test_config_singleton(self) -> None:
        reset_database_config()
        c1 = get_database_config()
        c2 = get_database_config()
        assert c1 is c2

    def test_config_custom(self) -> None:
        config = DatabaseConfig(
            database_url="sqlite+aiosqlite://",
            pool_size=5,
            max_overflow=5,
        )
        assert config.pool_size == 5


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class TestModels:
    def test_base_exists(self) -> None:
        assert Base is not None

    def test_user_model_table(self) -> None:
        assert UserModel.__tablename__ == "users"

    def test_api_key_model_table(self) -> None:
        assert APIKeyModel.__tablename__ == "api_keys"

    def test_memory_model_table(self) -> None:
        assert MemoryModel.__tablename__ == "memories"

    def test_goal_model_table(self) -> None:
        assert GoalModel.__tablename__ == "goals"

    def test_audit_log_model_table(self) -> None:
        assert AuditLogModel.__tablename__ == "audit_logs"

    def test_session_model_table(self) -> None:
        assert SessionModel.__tablename__ == "sessions"


# ---------------------------------------------------------------------------
# Repository Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestUserRepository:
    async def test_create_user(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        user = await repo.create(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed123",
        )
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.is_superuser is False

    async def test_get_by_email(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        await repo.create(
            email="find@example.com",
            username="findme",
            hashed_password="hashed",
        )
        found = await repo.get_by_email("find@example.com")
        assert found is not None
        assert found.username == "findme"

    async def test_get_by_email_not_found(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        found = await repo.get_by_email("nonexistent@example.com")
        assert found is None

    async def test_get_by_username(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        await repo.create(
            email="user@example.com",
            username="specificuser",
            hashed_password="hashed",
        )
        found = await repo.get_by_username("specificuser")
        assert found is not None

    async def test_count_users(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        assert await repo.count() == 0
        await repo.create(email="a@b.com", username="a", hashed_password="h")
        await repo.create(email="b@b.com", username="b", hashed_password="h")
        assert await repo.count() == 2


@pytest.mark.asyncio
class TestMemoryRepository:
    async def test_create_memory(self, session: AsyncSession) -> None:
        repo = MemoryRepository(session)
        memory = await repo.create(
            content="Test memory content",
            memory_type="episodic",
            importance=0.8,
        )
        assert memory.id is not None
        assert memory.content == "Test memory content"

    async def test_search_memories(self, session: AsyncSession) -> None:
        repo = MemoryRepository(session)
        await repo.create(content="Python is a programming language")
        await repo.create(content="JavaScript is used for web")
        await repo.create(content="I like cats")

        results = await repo.search("Python")
        assert len(results) == 1
        assert "Python" in results[0].content

    async def test_get_recent(self, session: AsyncSession) -> None:
        repo = MemoryRepository(session)
        await repo.create(content="Memory 1")
        await repo.create(content="Memory 2")
        await repo.create(content="Memory 3")

        recent = await repo.get_recent(limit=2)
        assert len(recent) == 2


@pytest.mark.asyncio
class TestGoalRepository:
    async def test_create_goal(self, session: AsyncSession) -> None:
        repo = GoalRepository(session)
        goal = await repo.create(
            title="Test Goal",
            description="A test goal",
            priority=5,
        )
        assert goal.id is not None
        assert goal.title == "Test Goal"
        assert goal.status == "pending"
        assert goal.progress == 0.0

    async def test_list_by_status(self, session: AsyncSession) -> None:
        repo = GoalRepository(session)
        await repo.create(title="Pending 1")
        g2 = await repo.create(title="In Progress")
        g3 = await repo.create(title="In Progress 2")

        # Update status
        await repo.update_progress(g2.id, 0.5, status="in_progress")
        await repo.update_progress(g3.id, 1.0, status="completed")

        pending = await repo.list_by_status("pending")
        assert len(pending) == 1
        assert pending[0].title == "Pending 1"

        completed = await repo.list_by_status("completed")
        assert len(completed) == 1
        assert completed[0].title == "In Progress 2"


@pytest.mark.asyncio
class TestAuditLogRepository:
    async def test_create_audit_log(self, session: AsyncSession) -> None:
        repo = AuditLogRepository(session)
        log = await repo.create(
            action="user.login",
            details={"method": "password"},
            ip_address="127.0.0.1",
        )
        assert log.id is not None
        assert log.action == "user.login"
        assert log.status == "success"

    async def test_query_logs(self, session: AsyncSession) -> None:
        repo = AuditLogRepository(session)
        await repo.create(action="user.login")
        await repo.create(action="user.logout")
        await repo.create(action="user.login")

        login_logs = await repo.query(action="user.login")
        assert len(login_logs) == 2

        logout_logs = await repo.query(action="user.logout")
        assert len(logout_logs) == 1


@pytest.mark.asyncio
class TestSessionRepository:
    async def test_create_session(self, session: AsyncSession) -> None:
        # First create a user
        user_repo = UserRepository(session)
        user = await user_repo.create(
            email="session@example.com",
            username="sessionuser",
            hashed_password="hashed",
        )

        repo = SessionRepository(session)
        sess = await repo.create(
            user_id=user.id,
            token_jti="test-jti-123",
            expires_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        assert sess.id is not None
        assert sess.token_jti == "test-jti-123"

    async def test_revoke_session(self, session: AsyncSession) -> None:
        user_repo = UserRepository(session)
        user = await user_repo.create(
            email="revoke@example.com",
            username="revokeuser",
            hashed_password="hashed",
        )

        repo = SessionRepository(session)
        sess = await repo.create(
            user_id=user.id,
            token_jti="revoke-jti",
            expires_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )

        revoked = await repo.revoke_by_jti("revoke-jti")
        assert revoked is True

        found = await repo.get_by_jti("revoke-jti")
        assert found is not None
        assert found.revoked_at is not None


@pytest.mark.asyncio
class TestAPIKeyRepository:
    async def test_create_api_key(self, session: AsyncSession) -> None:
        user_repo = UserRepository(session)
        user = await user_repo.create(
            email="apikey@example.com",
            username="apikeyuser",
            hashed_password="hashed",
        )

        repo = APIKeyRepository(session)
        key = await repo.create(
            user_id=user.id,
            name="Test Key",
            key_hash="abc123hash",
            key_prefix="ak_test",
        )
        assert key.id is not None
        assert key.name == "Test Key"
        assert key.is_active is True

    async def test_list_keys_for_user(self, session: AsyncSession) -> None:
        user_repo = UserRepository(session)
        user = await user_repo.create(
            email="list@example.com",
            username="listuser",
            hashed_password="hashed",
        )

        repo = APIKeyRepository(session)
        await repo.create(user_id=user.id, name="Key 1", key_hash="hash1", key_prefix="ak_1")
        await repo.create(user_id=user.id, name="Key 2", key_hash="hash2", key_prefix="ak_2")

        keys = await repo.list_for_user(user.id)
        assert len(keys) == 2

    async def test_deactivate_key(self, session: AsyncSession) -> None:
        user_repo = UserRepository(session)
        user = await user_repo.create(
            email="deactivate@example.com",
            username="deactivateuser",
            hashed_password="hashed",
        )

        repo = APIKeyRepository(session)
        key = await repo.create(
            user_id=user.id,
            name="Deactivate Key",
            key_hash="deactivate-hash",
            key_prefix="ak_del",
        )

        deactivated = await repo.deactivate(key.id)
        assert deactivated is True

        found = await repo.get_by_id(key.id)
        assert found.is_active is False
