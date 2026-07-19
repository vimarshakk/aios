"""Priority queues — multi-level priority support for task scheduling.

Extends the base queue with strict priority ordering, ensuring
critical tasks are always processed before lower-priority work.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aios.distributed.queue import TaskMessage


class Priority(IntEnum):
    """Named priority levels (lower number = higher priority)."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 5
    LOW = 9
    BACKGROUND = 15


@dataclass
class PriorityQueue:
    """Multi-level priority queue backed by an in-memory deque per level.

    Tasks are dequeued in strict priority order (lowest number first),
    with FIFO ordering within the same priority level.

    Usage::

        pq = PriorityQueue()
        await pq.push(TaskMessage(payload={"cmd": "urgent"}, priority=Priority.CRITICAL))
        await pq.push(TaskMessage(payload={"cmd": "normal"}, priority=Priority.NORMAL))
        msg = await pq.pop()  # Returns the CRITICAL task first
    """

    _queues: dict[int, asyncio.Queue[TaskMessage]] = field(default_factory=dict)
    _priority_order: list[int] = field(default_factory=list)
    _total_size: int = 0

    def __post_init__(self) -> None:
        self._ensure_queues()

    def _ensure_queues(self) -> None:
        """Ensure queues exist for all priority levels."""
        for level in Priority:
            if level not in self._queues:
                self._queues[level] = asyncio.Queue()
                if level not in self._priority_order:
                    self._priority_order.append(level)
        self._priority_order.sort()

    async def push(self, message: TaskMessage) -> None:
        """Enqueue a task message at its priority level."""
        level = message.priority
        if level not in self._queues:
            self._queues[level] = asyncio.Queue()
            self._priority_order.append(level)
            self._priority_order.sort()
        await self._queues[level].put(message)
        self._total_size += 1

    async def pop(self, timeout: float = 1.0) -> TaskMessage | None:
        """Dequeue the highest-priority task.

        Returns tasks in strict priority order (lowest number first),
        with FIFO ordering within each priority level.

        Returns:
            The highest-priority task message, or None if empty.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            for level in self._priority_order:
                q = self._queues.get(level)
                if q and not q.empty():
                    msg = q.get_nowait()
                    self._total_size -= 1
                    return msg
            await asyncio.sleep(0.01)
        return None

    async def peek(self, count: int = 10) -> list[TaskMessage]:
        """Look at up to `count` tasks in priority order without removing them."""
        result: list[TaskMessage] = []
        for level in self._priority_order:
            q = self._queues.get(level)
            if q:
                items = list(q._queue)
                result.extend(items[: count - len(result)])
                if len(result) >= count:
                    break
        return result

    def size(self) -> int:
        """Total number of tasks across all priority levels."""
        return self._total_size

    def size_by_priority(self) -> dict[str, int]:
        """Task count per priority level."""
        result: dict[str, int] = {}
        for level in self._priority_order:
            q = self._queues.get(level)
            if q and not q.empty():
                result[Priority(level).name] = q.qsize()
        return result

    async def purge(self, priority: Priority | None = None) -> int:
        """Remove all tasks, optionally filtered by priority level.

        Returns:
            Number of tasks removed.
        """
        removed = 0
        if priority:
            q = self._queues.get(priority)
            if q:
                removed = q.qsize()
                while not q.empty():
                    q.get_nowait()
                self._total_size -= removed
        else:
            for level in self._priority_order:
                q = self._queues.get(level)
                if q:
                    removed += q.qsize()
                    while not q.empty():
                        q.get_nowait()
            self._total_size = 0
        return removed

    def has_critical(self) -> bool:
        """Check if there are any CRITICAL priority tasks pending."""
        q = self._queues.get(Priority.CRITICAL)
        return q is not None and not q.empty()

    def highest_priority(self) -> Priority | None:
        """Get the highest priority level with pending tasks."""
        for level in self._priority_order:
            q = self._queues.get(level)
            if q and not q.empty():
                return Priority(level)
        return None


__all__ = [
    "Priority",
    "PriorityQueue",
]
