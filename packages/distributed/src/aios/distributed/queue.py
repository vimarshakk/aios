"""Redis-backed task queue with in-memory fallback.

Provides a consistent interface for enqueueing and dequeueing task messages,
with automatic serialization, TTL support, and consumer groups via Redis Lists
or a simple in-memory deque for single-process mode.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from enum import IntEnum
from typing import Any

from redis.asyncio import Redis


class TaskPriority(IntEnum):
    """Numeric task priorities (lower = higher priority)."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 5
    LOW = 9
    BACKGROUND = 15


@dataclass
class TaskMessage:
    """A task message in the queue.

    Attributes:
        id: Unique task identifier.
        queue: Target queue name.
        payload: Task payload (must be JSON-serializable).
        priority: Numeric priority (lower = higher).
        enqueued_at: Timestamp when the task was enqueued.
        visible_at: Earliest time the task becomes visible (for delayed tasks).
        ttl_seconds: Time-to-live in seconds; 0 means no expiry.
        attempt: Current attempt number (0-based).
        correlation_id: Optional correlation ID for request tracing.
        metadata: Arbitrary metadata attached to the task.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    queue: str = "default"
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = TaskPriority.NORMAL
    enqueued_at: float = field(default_factory=time.time)
    visible_at: float = 0.0
    ttl_seconds: int = 0
    attempt: int = 0
    correlation_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.visible_at == 0.0:
            self.visible_at = self.enqueued_at

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str | bytes) -> TaskMessage:
        data = json.loads(raw)
        return cls(**data)

    def is_visible(self) -> bool:
        return time.time() >= self.visible_at

    def is_expired(self) -> bool:
        if self.ttl_seconds <= 0:
            return False
        return time.time() > self.enqueued_at + self.ttl_seconds


class QueueBackend:
    """Abstract queue backend interface."""

    async def push(self, message: TaskMessage) -> None:
        raise NotImplementedError

    async def pop(self, queue: str = "default", timeout: float = 1.0) -> TaskMessage | None:
        raise NotImplementedError

    async def ack(self, message: TaskMessage) -> None:
        raise NotImplementedError

    async def nack(self, message: TaskMessage) -> None:
        raise NotImplementedError

    async def size(self, queue: str = "default") -> int:
        raise NotImplementedError

    async def peek(self, queue: str = "default", count: int = 10) -> list[TaskMessage]:
        raise NotImplementedError

    async def purge(self, queue: str = "default") -> int:
        raise NotImplementedError

    async def close(self) -> None:
        pass


class InMemoryQueue(QueueBackend):
    """In-memory queue using deque — for single-process testing."""

    def __init__(self) -> None:
        self._queues: dict[str, deque[TaskMessage]] = {}
        self._processing: dict[str, deque[TaskMessage]] = {}
        self._sizes: dict[str, int] = {}

    def _get_queue(self, name: str) -> deque[TaskMessage]:
        if name not in self._queues:
            self._queues[name] = deque()
            self._processing[name] = deque()
            self._sizes[name] = 0
        return self._queues[name]

    async def push(self, message: TaskMessage) -> None:
        q = self._get_queue(message.queue)
        q.append(message)
        self._sizes[message.queue] = len(q)

    async def pop(self, queue: str = "default", timeout: float = 1.0) -> TaskMessage | None:
        q = self._get_queue(queue)
        deadline = time.time() + timeout
        while time.time() < deadline:
            while q:
                msg = q.popleft()
                self._sizes[queue] = len(q)
                if msg.is_visible() and not msg.is_expired():
                    self._processing[queue].append(msg)
                    return msg
            await asyncio.sleep(0.01)
        return None

    async def ack(self, message: TaskMessage) -> None:
        q = self._processing.get(message.queue, deque())
        with contextlib.suppress(ValueError):
            q.remove(message)

    async def nack(self, message: TaskMessage) -> None:
        q = self._processing.get(message.queue, deque())
        with contextlib.suppress(ValueError):
            q.remove(message)
        message.visible_at = time.time()
        await self.push(message)

    async def size(self, queue: str = "default") -> int:
        q = self._get_queue(queue)
        return len(q)

    async def peek(self, queue: str = "default", count: int = 10) -> list[TaskMessage]:
        q = self._get_queue(queue)
        visible = [m for m in q if m.is_visible() and not m.is_expired()]
        return visible[:count]

    async def purge(self, queue: str = "default") -> int:
        q = self._get_queue(queue)
        count = len(q)
        q.clear()
        self._sizes[queue] = 0
        return count


class RedisQueue(QueueBackend):
    """Redis-backed task queue using Lists and sorted sets.

    Uses Redis Lists (LPUSH/BRPOP) for FIFO ordering with priority support.
    For delayed tasks, uses a sorted set with score = visible_at timestamp.
    """

    QUEUE_PREFIX = "aios:queue:"
    DELAYED_PREFIX = "aios:delayed:"
    PROCESSING_PREFIX = "aios:processing:"

    def __init__(self, client: Redis) -> None:
        self._redis = client

    @classmethod
    async def create(cls, url: str = "redis://localhost:6379/0") -> RedisQueue:
        client = Redis.from_url(url, decode_responses=True)
        return cls(client)

    def _queue_key(self, queue: str) -> str:
        return f"{self.QUEUE_PREFIX}{queue}"

    def _delayed_key(self, queue: str) -> str:
        return f"{self.DELAYED_PREFIX}{queue}"

    def _processing_key(self, queue: str) -> str:
        return f"{self.PROCESSING_PREFIX}{queue}"

    async def push(self, message: TaskMessage) -> None:
        raw = message.to_json()
        if message.visible_at > time.time():
            score = message.visible_at
            await self._redis.zadd(self._delayed_key(message.queue), {raw: score})
        else:
            await self._redis.lpush(self._queue_key(message.queue), raw)

    async def pop(self, queue: str = "default", timeout: float = 1.0) -> TaskMessage | None:
        await self._move_delayed(queue)
        raw = await self._redis.brpop(self._queue_key(queue), timeout=timeout)
        if raw is None:
            return None
        _, value = raw
        msg = TaskMessage.from_json(value)
        await self._redis.set(
            self._processing_key(msg.id),
            msg.to_json(),
            ex=max(msg.ttl_seconds, 300),
        )
        return msg

    async def ack(self, message: TaskMessage) -> None:
        await self._redis.delete(self._processing_key(message.id))

    async def nack(self, message: TaskMessage) -> None:
        await self._redis.delete(self._processing_key(message.id))
        message.visible_at = time.time()
        await self.push(message)

    async def size(self, queue: str = "default") -> int:
        return await self._redis.llen(self._queue_key(queue))

    async def peek(self, queue: str = "default", count: int = 10) -> list[TaskMessage]:
        raw_list = await self._redis.lrange(self._queue_key(queue), 0, count - 1)
        return [TaskMessage.from_json(r) for r in raw_list]

    async def purge(self, queue: str = "default") -> int:
        key = self._queue_key(queue)
        count = await self._redis.llen(key)
        await self._redis.delete(key)
        return count

    async def _move_delayed(self, queue: str) -> None:
        now = time.time()
        delayed_key = self._delayed_key(queue)
        ready = await self._redis.zrangebyscore(delayed_key, "-inf", now)
        if ready:
            pipe = self._redis.pipeline()
            for raw in ready:
                pipe.lpush(self._queue_key(queue), raw)
                pipe.zrem(delayed_key, raw)
            await pipe.execute()

    async def close(self) -> None:
        await self._redis.aclose()


__all__ = [
    "InMemoryQueue",
    "QueueBackend",
    "RedisQueue",
    "TaskMessage",
    "TaskPriority",
]
