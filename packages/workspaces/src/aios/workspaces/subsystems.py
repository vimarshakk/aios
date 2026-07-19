"""AIOS Workspaces — sub-systems composing the workspace execution context.

Each sub-system reuses an existing platform package rather than reimplementing
storage or skills (ADR-0019):

* **memory** — short-lived key/value scratch space (workspace-local).
* **artifacts** — typed artifact store scoped to the workspace.
* **history** — append-only audit log of workspace actions.
* **cache** — TTL-free in-memory cache with explicit invalidation.
* **permissions** — a scoped :class:`PermissionSet` for the workspace.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aios.artifacts import ArtifactKind, ArtifactStore


class WorkspaceMemory:
    """Ephemeral key/value scratch space for a workspace session."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def delete(self, key: str) -> bool:
        return self._data.pop(key, None) is not None

    def keys(self) -> list[str]:
        return list(self._data.keys())

    def clear(self) -> None:
        self._data.clear()


@dataclass
class HistoryEntry:
    """A single entry in the workspace action history."""

    timestamp: float
    action: str
    detail: str = ""
    actor: str = "system"


class WorkspaceHistory:
    """Append-only audit log of workspace actions."""

    def __init__(self) -> None:
        self._entries: list[HistoryEntry] = []

    def record(self, action: str, detail: str = "", actor: str = "system") -> HistoryEntry:
        entry = HistoryEntry(timestamp=time.time(), action=action, detail=detail, actor=actor)
        self._entries.append(entry)
        return entry

    def since(self, timestamp: float) -> list[HistoryEntry]:
        return [e for e in self._entries if e.timestamp >= timestamp]

    @property
    def entries(self) -> list[HistoryEntry]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries.clear()


class WorkspaceCache:
    """Simple in-memory cache with explicit invalidation."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def put(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def invalidate(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def keys(self) -> list[str]:
        return list(self._store.keys())

    def clear(self) -> None:
        self._store.clear()


@dataclass
class WorkspacePermissions:
    """Scoped permission set for a workspace session."""

    granted: tuple[str, ...] = ()

    def allows(self, permission: str) -> bool:
        return permission in self.granted

    def union(self, other: WorkspacePermissions) -> WorkspacePermissions:
        return WorkspacePermissions(granted=tuple(set(self.granted) | set(other.granted)))


@dataclass
class WorkspaceArtifacts:
    """Typed artifact helper scoped to a workspace (wraps a store)."""

    store: ArtifactStore
    workspace_id: str = ""

    def save(
        self,
        name: str,
        content: bytes | str,
        kind: ArtifactKind | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        meta = dict(metadata or {})
        meta.setdefault("workspace", self.workspace_id)
        return self.store.put(name, content, kind=kind, metadata=meta)


__all__ = [
    "HistoryEntry",
    "WorkspaceArtifacts",
    "WorkspaceCache",
    "WorkspaceHistory",
    "WorkspaceMemory",
    "WorkspacePermissions",
]
