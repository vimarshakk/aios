"""Dead-letter queue for permanently failed tasks.

Stores tasks that have exhausted all retry attempts or hit non-retryable errors,
with structured metadata for debugging and replay capabilities.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from aios.distributed.queue import TaskMessage


@dataclass
class DeadLetterEntry:
    """A task in the dead-letter queue.

    Attributes:
        id: Unique DLQ entry identifier.
        original_task: The original task message that failed.
        error: The error message that caused the failure.
        error_type: Exception class name.
        failed_at: Timestamp when the task permanently failed.
        total_attempts: How many times the task was attempted.
        source_queue: The queue the task originally came from.
        stacktrace: Full traceback string if available.
        metadata: Additional context about the failure.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    original_task: TaskMessage = field(default_factory=TaskMessage)
    error: str = ""
    error_type: str = ""
    failed_at: float = field(default_factory=time.time)
    total_attempts: int = 0
    source_queue: str = "default"
    stacktrace: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["original_task"] = asdict(self.original_task)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeadLetterEntry:
        task_data = data.pop("original_task", {})
        return cls(
            original_task=TaskMessage(**task_data),
            **{k: v for k, v in data.items() if k in cls.__dataclass_fields__},
        )


class DeadLetterQueue:
    """In-memory dead-letter queue with structured storage and replay.

    Stores failed tasks with full error context and provides
    query, replay, and purge capabilities.

    Usage::

        dlq = DeadLetterQueue()
        await dlq.push(entry)
        entries = dlq.query(source_queue="llm")
        await dlq.replay(entry.id, queue_backend)
    """

    def __init__(self, max_size: int = 10_000) -> None:
        self._entries: list[DeadLetterEntry] = []
        self._index: dict[str, DeadLetterEntry] = {}
        self._max_size = max_size

    async def push(self, entry: DeadLetterEntry) -> None:
        """Add a failed task to the DLQ.

        If the DLQ exceeds max_size, the oldest entry is evicted.
        """
        if len(self._entries) >= self._max_size:
            evicted = self._entries.pop(0)
            self._index.pop(evicted.id, None)
        self._entries.append(entry)
        self._index[entry.id] = entry

    async def pop(self) -> DeadLetterEntry | None:
        """Remove and return the oldest DLQ entry."""
        if not self._entries:
            return None
        entry = self._entries.pop(0)
        self._index.pop(entry.id, None)
        return entry

    def get(self, entry_id: str) -> DeadLetterEntry | None:
        """Get a DLQ entry by ID."""
        return self._index.get(entry_id)

    def query(
        self,
        source_queue: str | None = None,
        error_type: str | None = None,
        since: float | None = None,
        limit: int = 100,
    ) -> list[DeadLetterEntry]:
        """Query DLQ entries with optional filters.

        Args:
            source_queue: Filter by original queue name.
            error_type: Filter by exception class name.
            since: Filter entries newer than this timestamp.
            limit: Maximum results to return.
        """
        results = self._entries
        if source_queue:
            results = [e for e in results if e.source_queue == source_queue]
        if error_type:
            results = [e for e in results if e.error_type == error_type]
        if since:
            results = [e for e in results if e.failed_at >= since]
        return results[-limit:]

    async def replay(self, entry_id: str, queue_backend: Any) -> bool:
        """Requeue a DLQ entry back to its original queue.

        Args:
            entry_id: ID of the DLQ entry to replay.
            queue_backend: The queue backend to push to.

        Returns:
            True if the entry was replayed, False if not found.
        """
        entry = self._index.get(entry_id)
        if entry is None:
            return False
        task = entry.original_task
        task.attempt = 0
        task.visible_at = time.time()
        await queue_backend.push(task)
        self._entries.remove(entry)
        del self._index[entry_id]
        return True

    async def purge(self, source_queue: str | None = None) -> int:
        """Remove all DLQ entries, optionally filtered by source queue.

        Returns:
            Number of entries removed.
        """
        if source_queue is None:
            count = len(self._entries)
            self._entries.clear()
            self._index.clear()
            return count
        to_remove = [e for e in self._entries if e.source_queue == source_queue]
        for entry in to_remove:
            self._entries.remove(entry)
            self._index.pop(entry.id, None)
        return len(to_remove)

    @property
    def size(self) -> int:
        """Current number of entries in the DLQ."""
        return len(self._entries)

    def stats(self) -> dict[str, Any]:
        """Get DLQ statistics."""
        by_queue: dict[str, int] = {}
        by_error: dict[str, int] = {}
        for entry in self._entries:
            by_queue[entry.source_queue] = by_queue.get(entry.source_queue, 0) + 1
            by_error[entry.error_type] = by_error.get(entry.error_type, 0) + 1
        return {
            "total": len(self._entries),
            "by_queue": by_queue,
            "by_error_type": by_error,
            "max_size": self._max_size,
        }


__all__ = [
    "DeadLetterEntry",
    "DeadLetterQueue",
]
