"""Task persistence and recovery — JSON-file backed state snapshots.

Provides durable persistence for task state, enabling recovery after
process crashes and task auditing across restarts.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from aios.distributed.queue import TaskMessage


class TaskState(StrEnum):
    """Lifecycle states for a persisted task."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTERED = "dead_lettered"
    CANCELLED = "cancelled"


@dataclass
class TaskSnapshot:
    """A persisted snapshot of task state.

    Attributes:
        task: The task message.
        state: Current lifecycle state.
        created_at: When the snapshot was first created.
        updated_at: Last modification timestamp.
        attempts: Number of execution attempts.
        last_error: Most recent error message.
        last_error_type: Exception class name.
        result: Task result if completed.
        history: List of state transitions with timestamps.
    """

    task: TaskMessage = field(default_factory=TaskMessage)
    state: TaskState = TaskState.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    attempts: int = 0
    last_error: str = ""
    last_error_type: str = ""
    result: Any = None
    history: list[dict[str, Any]] = field(default_factory=list)

    def transition(self, new_state: TaskState, error: str = "", error_type: str = "") -> None:
        """Record a state transition."""
        self.history.append({
            "from": self.state.value,
            "to": new_state.value,
            "at": time.time(),
            "error": error,
        })
        self.state = new_state
        self.updated_at = time.time()
        if error:
            self.last_error = error
            self.last_error_type = error_type

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["task"] = asdict(self.task)
        d["state"] = self.state.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskSnapshot:
        task_data = data.pop("task", {})
        state = data.pop("state", TaskState.PENDING.value)
        return cls(
            task=TaskMessage(**task_data),
            state=TaskState(state),
            **{
                k: v for k, v in data.items()
                if k in cls.__dataclass_fields__ and k not in ("task", "state")
            },
        )


class TaskPersistence:
    """JSON-file backed task state persistence.

    Stores task snapshots as individual JSON files in a directory,
    with atomic writes and optional recovery on startup.

    Usage::

        persistence = TaskPersistence("/var/lib/aios/tasks")
        await persistence.save(snapshot)
        recovered = await persistence.recover_pending()
    """

    def __init__(self, directory: str | Path) -> None:
        self._dir = Path(directory)
        self._snapshots: dict[str, TaskSnapshot] = {}
        self._initialized = False

    @property
    def directory(self) -> Path:
        return self._dir

    async def initialize(self) -> None:
        """Create the persistence directory and load existing snapshots."""
        self._dir.mkdir(parents=True, exist_ok=True)
        await self._load_all()
        self._initialized = True

    async def save(self, snapshot: TaskSnapshot) -> None:
        """Persist a task snapshot to disk and in-memory cache."""
        self._snapshots[snapshot.task.id] = snapshot
        path = self._snapshot_path(snapshot.task.id)
        data = json.dumps(snapshot.to_dict(), indent=2, default=str)
        tmp_path = path.with_suffix(".tmp")
        await asyncio.to_thread(tmp_path.write_text, data)
        await asyncio.to_thread(tmp_path.replace, path)

    async def load(self, task_id: str) -> TaskSnapshot | None:
        """Load a task snapshot by ID."""
        if task_id in self._snapshots:
            return self._snapshots[task_id]
        path = self._snapshot_path(task_id)
        if not path.exists():
            return None
        raw = await asyncio.to_thread(path.read_text)
        snapshot = TaskSnapshot.from_dict(json.loads(raw))
        self._snapshots[task_id] = snapshot
        return snapshot

    async def delete(self, task_id: str) -> bool:
        """Remove a task snapshot from disk and cache."""
        self._snapshots.pop(task_id, None)
        path = self._snapshot_path(task_id)
        if path.exists():
            await asyncio.to_thread(path.unlink)
            return True
        return False

    async def recover_pending(self) -> list[TaskSnapshot]:
        """Recover tasks in non-terminal states (pending, queued, processing, retrying).

        Returns:
            List of snapshots that need recovery.
        """
        if not self._initialized:
            await self.initialize()
        terminal = {
            TaskState.COMPLETED, TaskState.FAILED,
            TaskState.DEAD_LETTERED, TaskState.CANCELLED,
        }
        pending = [
            s for s in self._snapshots.values()
            if s.state not in terminal
        ]
        for snap in pending:
            if snap.state == TaskState.PROCESSING:
                snap.transition(
                    TaskState.RETRYING,
                    error="Process interrupted",
                    error_type="RecoveryError",
                )
                await self.save(snap)
        return pending

    async def list_tasks(
        self,
        state: TaskState | None = None,
        limit: int = 100,
    ) -> list[TaskSnapshot]:
        """List persisted task snapshots with optional state filter."""
        if not self._initialized:
            await self.initialize()
        results = list(self._snapshots.values())
        if state:
            results = [s for s in results if s.state == state]
        results.sort(key=lambda s: s.updated_at, reverse=True)
        return results[:limit]

    async def count_by_state(self) -> dict[str, int]:
        """Count tasks in each state."""
        counts: dict[str, int] = {}
        for snap in self._snapshots.values():
            counts[snap.state.value] = counts.get(snap.state.value, 0) + 1
        return counts

    def _snapshot_path(self, task_id: str) -> Path:
        return self._dir / f"{task_id}.json"

    async def _load_all(self) -> None:
        """Load all snapshots from disk."""
        if not self._dir.exists():
            return
        files = await asyncio.to_thread(
            lambda: list(self._dir.glob("*.json"))
        )
        for path in files:
            try:
                raw = await asyncio.to_thread(path.read_text)
                snapshot = TaskSnapshot.from_dict(json.loads(raw))
                self._snapshots[snapshot.task.id] = snapshot
            except (json.JSONDecodeError, KeyError):
                continue


__all__ = [
    "TaskPersistence",
    "TaskSnapshot",
    "TaskState",
]
