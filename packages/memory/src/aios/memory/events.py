"""Memory lifecycle events — published by HybridMemoryManager and backends."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MemoryEventType(StrEnum):
    """Types of memory lifecycle events."""

    STORED = "memory.stored"
    RETRIEVED = "memory.retrieved"
    UPDATED = "memory.updated"
    DELETED = "memory.deleted"
    CLEARED = "memory.cleared"
    SUMMARIZED = "memory.summarized"
    EXPIRED = "memory.expired"
    QUERIED = "memory.queried"


@dataclass
class MemoryEvent:
    """A memory lifecycle event."""

    event_type: MemoryEventType
    backend: str  # e.g. "short_term", "episodic", "entity", "hybrid"
    content: str = ""
    doc_id: str = ""
    query: str = ""
    result_count: int = 0
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()


def memory_stored(backend: str, doc_id: str, content: str, **meta: Any) -> MemoryEvent:
    """Create a MemoryStored event."""
    return MemoryEvent(
        event_type=MemoryEventType.STORED,
        backend=backend,
        doc_id=doc_id,
        content=content[:200],
        metadata=meta,
    )


def memory_retrieved(
    backend: str, query: str, result_count: int, **meta: Any
) -> MemoryEvent:
    """Create a MemoryRetrieved event."""
    return MemoryEvent(
        event_type=MemoryEventType.RETRIEVED,
        backend=backend,
        query=query,
        result_count=result_count,
        metadata=meta,
    )


def memory_deleted(backend: str, doc_id: str) -> MemoryEvent:
    """Create a MemoryDeleted event."""
    return MemoryEvent(
        event_type=MemoryEventType.DELETED,
        backend=backend,
        doc_id=doc_id,
    )


def memory_cleared(backend: str) -> MemoryEvent:
    """Create a MemoryCleared event."""
    return MemoryEvent(
        event_type=MemoryEventType.CLEARED,
        backend=backend,
    )


def memory_summarized(backend: str, doc_id: str, content: str) -> MemoryEvent:
    """Create a MemorySummarized event."""
    return MemoryEvent(
        event_type=MemoryEventType.SUMMARIZED,
        backend=backend,
        doc_id=doc_id,
        content=content[:200],
    )


def memory_expired(backend: str, doc_id: str) -> MemoryEvent:
    """Create a MemoryExpired event."""
    return MemoryEvent(
        event_type=MemoryEventType.EXPIRED,
        backend=backend,
        doc_id=doc_id,
    )


def memory_queried(
    backend: str, query: str, result_count: int, **meta: Any
) -> MemoryEvent:
    """Create a MemoryQueried event."""
    return MemoryEvent(
        event_type=MemoryEventType.QUERIED,
        backend=backend,
        query=query,
        result_count=result_count,
        metadata=meta,
    )
