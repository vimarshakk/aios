"""ShortTermMemory — in-memory sliding window for recent conversation context."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from aios.memory.backend import MemoryBackend, RetrievalResult


@dataclass
class _Entry:
    """Internal storage entry."""

    id: str
    content: str
    metadata: dict[str, Any]
    created_at: float


class ShortTermMemory(MemoryBackend):
    """In-memory sliding window for recent conversation turns.

    Stores entries in a list with a configurable max size. When the limit
    is reached, the oldest entries are evicted. Supports simple substring
    matching for retrieval (no embeddings needed).
    """

    def __init__(self, max_entries: int = 100) -> None:
        self._max_entries = max_entries
        self._entries: list[_Entry] = []

    def _evict(self) -> None:
        """Remove oldest entries if over capacity."""
        while len(self._entries) > self._max_entries:
            self._entries.pop(0)

    async def store(self, content: str, *, metadata: dict[str, Any] | None = None) -> str:
        doc_id = uuid.uuid4().hex[:12]
        entry = _Entry(
            id=doc_id,
            content=content,
            metadata=metadata or {},
            created_at=time.time(),
        )
        self._entries.append(entry)
        self._evict()
        return doc_id

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[RetrievalResult]:
        query_lower = query.lower()
        scored: list[tuple[float, _Entry]] = []

        for entry in self._entries:
            content_lower = entry.content.lower()
            if query_lower in content_lower:
                # Exact substring match gets high score
                score = 0.9
            elif any(w in content_lower for w in query_lower.split()):
                # Word overlap gets medium score
                query_words = set(query_lower.split())
                content_words = set(content_lower.split())
                overlap = len(query_words & content_words)
                score = min(0.8, 0.3 + 0.15 * overlap) if overlap > 0 else 0.0
            else:
                score = 0.0

            if score > 0 and score >= min_score:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            RetrievalResult(
                content=e.content,
                score=s,
                metadata=e.metadata,
                source="short_term",
                doc_id=e.id,
                created_at=e.created_at,
            )
            for s, e in scored[:top_k]
        ]

    async def delete(self, doc_id: str) -> bool:
        for i, entry in enumerate(self._entries):
            if entry.id == doc_id:
                self._entries.pop(i)
                return True
        return False

    async def clear(self) -> None:
        self._entries.clear()

    async def count(self) -> int:
        return len(self._entries)

    async def has(self, doc_id: str) -> bool:
        return any(e.id == doc_id for e in self._entries)

    def get_recent(self, n: int = 10) -> list[dict[str, Any]]:
        """Return the N most recent entries as dicts."""
        recent = self._entries[-n:]
        return [
            {"id": e.id, "content": e.content, "metadata": e.metadata, "created_at": e.created_at}
            for e in recent
        ]
