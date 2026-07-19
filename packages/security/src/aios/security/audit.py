"""Audit logger — structured event logging for security and compliance."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class AuditLevel(StrEnum):
    """Audit event severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """A single audit log entry.

    Attributes:
        timestamp: Unix timestamp.
        level: Severity level.
        action: What happened (e.g. "plugin.install").
        actor: Who performed the action.
        target: What was acted upon.
        details: Additional structured data.
        success: Whether the action succeeded.
    """

    timestamp: float = field(default_factory=time.time)
    level: AuditLevel = AuditLevel.INFO
    action: str = ""
    actor: str = ""
    target: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    success: bool = True

    def to_dict(self) -> dict:
        """Serialize to a dict."""
        d = asdict(self)
        d["level"] = self.level.value
        return d

    def to_json(self) -> str:
        """Serialize to a JSON line."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """Append-only structured audit log.

    Stores events in memory and optionally persists to a JSONL file.
    """

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self._events: list[AuditEvent] = []
        self._storage_path = Path(storage_path) if storage_path else None
        if self._storage_path and self._storage_path.exists():
            self._load()

    def _load(self) -> None:
        if not self._storage_path or not self._storage_path.exists():
            return
        with self._storage_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                data["level"] = AuditLevel(data["level"])
                self._events.append(AuditEvent(**data))

    def _save(self) -> None:
        if not self._storage_path:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self._storage_path.open("w", encoding="utf-8") as f:
            for event in self._events:
                f.write(event.to_json() + "\n")

    def log(
        self,
        action: str,
        *,
        level: AuditLevel = AuditLevel.INFO,
        actor: str = "",
        target: str = "",
        details: dict[str, Any] | None = None,
        success: bool = True,
    ) -> AuditEvent:
        """Create and store an audit event."""
        event = AuditEvent(
            level=level,
            action=action,
            actor=actor,
            target=target,
            details=details or {},
            success=success,
        )
        self._events.append(event)
        self._save()
        return event

    def query(
        self,
        action: str | None = None,
        actor: str | None = None,
        level: AuditLevel | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Query events with optional filters."""
        results = self._events
        if action:
            results = [e for e in results if e.action == action]
        if actor:
            results = [e for e in results if e.actor == actor]
        if level:
            results = [e for e in results if e.level == level]
        return results[-limit:]

    def count(self, level: AuditLevel | None = None) -> int:
        """Count events, optionally filtered by level."""
        if level:
            return sum(1 for e in self._events if e.level == level)
        return len(self._events)

    def clear(self) -> None:
        """Clear all events."""
        self._events.clear()
        self._save()

    @property
    def events(self) -> list[AuditEvent]:
        """All events (read-only view)."""
        return list(self._events)
