"""Distributed locking and coordination via Redis.

Provides mutual exclusion, leader election, and resource locking
for distributed AIOS workers, preventing duplicate task execution.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redis.asyncio import Redis


class LockAcquisitionError(Exception):
    """Raised when a lock cannot be acquired within the timeout."""


class LockNotHeldError(Exception):
    """ Raised when trying to release a lock not held by this instance."""


@dataclass(frozen=True, slots=True)
class LockInfo:
    """Metadata about a distributed lock.

    Attributes:
        name: Lock resource name.
        holder: Unique ID of the lock holder.
        acquired_at: Timestamp when the lock was acquired.
        expires_at: Timestamp when the lock expires.
        ttl_seconds: Time-to-live for the lock.
    """

    name: str
    holder: str
    acquired_at: float
    expires_at: float
    ttl_seconds: int


class DistributedLock:
    """A single distributed lock backed by Redis SET with NX + EX.

    Usage::

        lock = DistributedLock(redis_client, "my-resource", ttl=30)
        if await lock.acquire():
            try:
                # critical section
            finally:
                await lock.release()
    """

    PREFIX = "aios:lock:"

    def __init__(
        self,
        client: Redis,
        name: str,
        ttl: int = 30,
        holder: str | None = None,
    ) -> None:
        self._redis = client
        self._name = name
        self._ttl = ttl
        self._holder = holder or uuid.uuid4().hex[:12]
        self._acquired_at: float | None = None
        self._key = f"{self.PREFIX}{name}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def holder(self) -> str:
        return self._holder

    @property
    def is_held(self) -> bool:
        return self._acquired_at is not None

    async def acquire(self, timeout: float = 5.0, retry_interval: float = 0.1) -> bool:
        """Acquire the lock with blocking retry.

        Args:
            timeout: Maximum seconds to wait for the lock.
            retry_interval: Seconds between acquisition attempts.

        Returns:
            True if the lock was acquired, False on timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            acquired = await self._redis.set(
                self._key,
                self._holder,
                nx=True,
                ex=self._ttl,
            )
            if acquired:
                self._acquired_at = time.time()
                return True
            await asyncio.sleep(retry_interval)
        return False

    async def try_acquire(self) -> bool:
        """Attempt to acquire the lock without blocking.

        Returns:
            True if acquired, False if already held.
        """
        acquired = await self._redis.set(
            self._key,
            self._holder,
            nx=True,
            ex=self._ttl,
        )
        if acquired:
            self._acquired_at = time.time()
        return bool(acquired)

    async def release(self) -> bool:
        """Release the lock (only if held by this holder).

        Returns:
            True if released, False if not held or held by another.
        """
        if self._acquired_at is None:
            return False
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = await self._redis.eval(script, 1, self._key, self._holder)
        self._acquired_at = None
        return bool(result)

    async def extend(self, additional_ttl: int | None = None) -> bool:
        """Extend the lock TTL (only if held by this holder).

        Args:
            additional_ttl: Additional seconds; if None, resets to original TTL.

        Returns:
            True if extended, False if not held or held by another.
        """
        ttl = additional_ttl or self._ttl
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        result = await self._redis.eval(script, 1, self._key, self._holder, str(ttl))
        return bool(result)

    async def is_locked(self) -> bool:
        """Check if the lock is currently held (by anyone)."""
        return await self._redis.exists(self._key) > 0

    async def info(self) -> LockInfo | None:
        """Get lock metadata if currently held."""
        holder = await self._redis.get(self._key)
        if not holder:
            return None
        ttl = await self._redis.ttl(self._key)
        now = time.time()
        return LockInfo(
            name=self._name,
            holder=holder,
            acquired_at=now - ttl,
            expires_at=now + ttl if ttl > 0 else now,
            ttl_seconds=self._ttl,
        )

    async def __aenter__(self) -> DistributedLock:
        acquired = await self.acquire()
        if not acquired:
            raise LockAcquisitionError(f"Could not acquire lock '{self._name}'")
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.release()


class LockManager:
    """Manages multiple distributed locks.

    Provides a factory for creating locks and tracks all active locks
    for a given worker instance.

    Usage::

        manager = LockManager(redis_client)
        async with manager.lock("resource-1", ttl=30):
            # critical section
            pass
    """

    def __init__(self, client: Redis, holder: str | None = None) -> None:
        self._redis = client
        self._holder = holder or uuid.uuid4().hex[:12]
        self._locks: dict[str, DistributedLock] = {}

    @property
    def holder(self) -> str:
        return self._holder

    def lock(self, name: str, ttl: int = 30) -> DistributedLock:
        """Create or return an existing lock for the given resource name."""
        if name not in self._locks:
            self._locks[name] = DistributedLock(
                self._redis, name, ttl=ttl, holder=self._holder,
            )
        return self._locks[name]

    def active_locks(self) -> list[str]:
        """List names of all locks currently held by this manager."""
        return [name for name, lock in self._locks.items() if lock.is_held]

    async def release_all(self) -> int:
        """Release all locks held by this manager.

        Returns:
            Number of locks released.
        """
        count = 0
        for lock in self._locks.values():
            if lock.is_held:
                await lock.release()
                count += 1
        return count

    async def cleanup(self) -> None:
        """Release all locks and clear the manager state."""
        await self.release_all()
        self._locks.clear()


class LeaderElection:
    """Simple leader election via distributed lock.

    Exactly one worker instance wins the leader lock at a time.
    Other instances can attempt to take over if the leader fails
    to extend its lease.

    Usage::

        election = LeaderElection(redis_client, "cluster-leader", ttl=15)
        if await election.become_leader():
            # this instance is the leader
            ...
    """

    def __init__(
        self,
        client: Redis,
        election_name: str = "leader",
        ttl: int = 15,
    ) -> None:
        self._lock = DistributedLock(client, f"election:{election_name}", ttl=ttl)
        self._leader_id: str | None = None

    @property
    def is_leader(self) -> bool:
        return self._lock.is_held

    @property
    def leader_id(self) -> str | None:
        return self._leader_id if self._lock.is_held else None

    async def become_leader(self, timeout: float = 0.0) -> bool:
        """Attempt to become the leader.

        Args:
            timeout: If > 0, retry for this many seconds.

        Returns:
            True if this instance is now the leader.
        """
        if timeout > 0:
            acquired = await self._lock.acquire(timeout=timeout)
        else:
            acquired = await self._lock.try_acquire()
        if acquired:
            self._leader_id = self._lock.holder
        return acquired

    async def resign(self) -> bool:
        """Resign from leadership."""
        result = await self._lock.release()
        self._leader_id = None
        return result

    async def extend_leadership(self) -> bool:
        """Extend the leader lease."""
        return await self._lock.extend()


__all__ = [
    "DistributedLock",
    "LeaderElection",
    "LockAcquisitionError",
    "LockInfo",
    "LockManager",
    "LockNotHeldError",
]
