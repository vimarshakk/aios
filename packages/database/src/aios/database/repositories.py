"""Repository layer — typed database access for each domain model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from aios.database.models import (
    APIKeyModel,
    AuditLogModel,
    Base,
    GoalModel,
    MemoryModel,
    SessionModel,
    UserModel,
)


class BaseRepository:
    """Base repository with common CRUD operations."""

    def __init__(self, session: AsyncSession, model: type[Base]) -> None:
        self.session = session
        self.model = model

    async def get_by_id(self, id: uuid.UUID) -> Any | None:
        """Get a record by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def count(self, **filters: Any) -> int:
        """Count records with optional filters."""
        query = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        result = await self.session.execute(query)
        return result.scalar_one()


class UserRepository(BaseRepository):
    """Repository for user operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserModel)

    async def get_by_email(self, email: str) -> UserModel | None:
        """Get a user by email."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> UserModel | None:
        """Get a user by username."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        username: str,
        hashed_password: str,
        roles: list[str] | None = None,
    ) -> UserModel:
        """Create a new user."""
        user = UserModel(
            email=email,
            username=username,
            hashed_password=hashed_password,
            roles=roles or ["user"],
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """Update user's last login timestamp."""
        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(updated_at=datetime.now(timezone.utc))
        )


class APIKeyRepository(BaseRepository):
    """Repository for API key operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, APIKeyModel)

    async def get_by_key_hash(self, key_hash: str) -> APIKeyModel | None:
        """Get an API key by its hash."""
        result = await self.session.execute(
            select(APIKeyModel).where(APIKeyModel.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> Sequence[APIKeyModel]:
        """List all API keys for a user."""
        result = await self.session.execute(
            select(APIKeyModel)
            .where(APIKeyModel.user_id == user_id)
            .order_by(APIKeyModel.created_at.desc())
        )
        return result.scalars().all()

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        key_hash: str,
        key_prefix: str,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> APIKeyModel:
        """Create a new API key."""
        key = APIKeyModel(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=scopes or [],
            expires_at=expires_at,
        )
        self.session.add(key)
        await self.session.flush()
        return key

    async def deactivate(self, key_id: uuid.UUID) -> bool:
        """Deactivate an API key."""
        result = await self.session.execute(
            update(APIKeyModel)
            .where(APIKeyModel.id == key_id)
            .values(is_active=False)
        )
        return result.rowcount > 0


class MemoryRepository(BaseRepository):
    """Repository for memory operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MemoryModel)

    async def create(
        self,
        content: str,
        memory_type: str = "episodic",
        user_id: uuid.UUID | None = None,
        metadata_json: dict[str, Any] | None = None,
        importance: float = 0.5,
    ) -> MemoryModel:
        """Create a new memory."""
        memory = MemoryModel(
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            metadata_json=metadata_json or {},
            importance=importance,
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def search(
        self,
        query: str,
        user_id: uuid.UUID | None = None,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> Sequence[MemoryModel]:
        """Search memories by content (simple text search)."""
        stmt = select(MemoryModel)
        if user_id:
            stmt = stmt.where(MemoryModel.user_id == user_id)
        if memory_type:
            stmt = stmt.where(MemoryModel.memory_type == memory_type)
        stmt = stmt.where(MemoryModel.content.ilike(f"%{query}%"))
        stmt = stmt.order_by(MemoryModel.importance.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_recent(
        self,
        user_id: uuid.UUID | None = None,
        limit: int = 20,
    ) -> Sequence[MemoryModel]:
        """Get recent memories."""
        stmt = select(MemoryModel)
        if user_id:
            stmt = stmt.where(MemoryModel.user_id == user_id)
        stmt = stmt.order_by(MemoryModel.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class GoalRepository(BaseRepository):
    """Repository for goal operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GoalModel)

    async def create(
        self,
        title: str,
        description: str | None = None,
        user_id: uuid.UUID | None = None,
        priority: int = 0,
    ) -> GoalModel:
        """Create a new goal."""
        goal = GoalModel(
            user_id=user_id,
            title=title,
            description=description,
            priority=priority,
        )
        self.session.add(goal)
        await self.session.flush()
        return goal

    async def list_by_status(
        self,
        status: str,
        user_id: uuid.UUID | None = None,
    ) -> Sequence[GoalModel]:
        """List goals by status."""
        stmt = select(GoalModel).where(GoalModel.status == status)
        if user_id:
            stmt = stmt.where(GoalModel.user_id == user_id)
        stmt = stmt.order_by(GoalModel.priority.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_progress(
        self,
        goal_id: uuid.UUID,
        progress: float,
        status: str | None = None,
    ) -> bool:
        """Update goal progress."""
        values: dict[str, Any] = {"progress": progress}
        if status:
            values["status"] = status
            if status == "completed":
                values["completed_at"] = datetime.now(timezone.utc)
        result = await self.session.execute(
            update(GoalModel).where(GoalModel.id == goal_id).values(**values)
        )
        return result.rowcount > 0


class AuditLogRepository(BaseRepository):
    """Repository for audit log operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AuditLogModel)

    async def create(
        self,
        action: str,
        user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        status: str = "success",
    ) -> AuditLogModel:
        """Create a new audit log entry."""
        log = AuditLogModel(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def query(
        self,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[AuditLogModel]:
        """Query audit logs with filters."""
        stmt = select(AuditLogModel)
        if user_id:
            stmt = stmt.where(AuditLogModel.user_id == user_id)
        if action:
            stmt = stmt.where(AuditLogModel.action == action)
        if resource_type:
            stmt = stmt.where(AuditLogModel.resource_type == resource_type)
        stmt = stmt.order_by(AuditLogModel.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class SessionRepository(BaseRepository):
    """Repository for session operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SessionModel)

    async def create(
        self,
        user_id: uuid.UUID,
        token_jti: str,
        expires_at: datetime,
    ) -> SessionModel:
        """Create a new session."""
        sess = SessionModel(
            user_id=user_id,
            token_jti=token_jti,
            expires_at=expires_at,
        )
        self.session.add(sess)
        await self.session.flush()
        return sess

    async def get_by_jti(self, jti: str) -> SessionModel | None:
        """Get a session by JWT ID."""
        result = await self.session.execute(
            select(SessionModel).where(SessionModel.token_jti == jti)
        )
        return result.scalar_one_or_none()

    async def revoke_by_jti(self, jti: str) -> bool:
        """Revoke a session by JWT ID."""
        result = await self.session.execute(
            update(SessionModel)
            .where(SessionModel.token_jti == jti)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """Revoke all sessions for a user. Returns count revoked."""
        result = await self.session.execute(
            update(SessionModel)
            .where(
                SessionModel.user_id == user_id,
                SessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        return result.rowcount
