"""EpisodicMemory — timestamped interaction memory for "what did we discuss" queries."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from aios.memory.backend import MemoryBackend, RetrievalResult


@dataclass
class Episode:
    """A single episodic memory entry."""

    id: str
    content: str
    timestamp: float
    session_id: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class EpisodicMemory(MemoryBackend):
    """Timestamped memory for tracking conversations and interactions.

    Useful for queries like "what did we discuss last time" or "when did
    I last talk about X". Stores entries with timestamps and optional
    session IDs for grouping.
    """

    def __init__(self, max_entries: int = 1000) -> None:
        self._max_entries = max_entries
        self._episodes: list[Episode] = []

    def _evict(self) -> None:
        while len(self._episodes) > self._max_entries:
            self._episodes.pop(0)

    async def store(
        self,
        content: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        meta = metadata or {}
        doc_id = uuid.uuid4().hex[:12]
        episode = Episode(
            id=doc_id,
            content=content,
            timestamp=meta.pop("timestamp", time.time()),
            session_id=meta.pop("session_id", ""),
            tags=meta.pop("tags", []),
            metadata=meta,
        )
        self._episodes.append(episode)
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
        scored: list[tuple[float, Episode]] = []

        for ep in self._episodes:
            content_lower = ep.content.lower()
            tag_match = any(t.lower() in query_lower for t in ep.tags)

            if query_lower in content_lower:
                score = 0.95 if tag_match else 0.85
            elif tag_match:
                score = 0.75
            elif any(w in content_lower for w in query_lower.split()):
                query_words = set(query_lower.split())
                content_words = set(content_lower.split())
                overlap = len(query_words & content_words)
                score = min(0.7, 0.2 + 0.15 * overlap) if overlap > 0 else 0.0
            else:
                score = 0.0

            if score >= min_score:
                scored.append((score, ep))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            RetrievalResult(
                content=ep.content,
                score=s,
                metadata={**ep.metadata, "session_id": ep.session_id, "tags": ep.tags},
                source="episodic",
                doc_id=ep.id,
                created_at=ep.timestamp,
            )
            for s, ep in scored[:top_k]
        ]

    async def delete(self, doc_id: str) -> bool:
        for i, ep in enumerate(self._episodes):
            if ep.id == doc_id:
                self._episodes.pop(i)
                return True
        return False

    async def clear(self) -> None:
        self._episodes.clear()

    async def count(self) -> int:
        return len(self._episodes)

    async def has(self, doc_id: str) -> bool:
        return any(ep.id == doc_id for ep in self._episodes)

    def get_by_session(self, session_id: str) -> list[Episode]:
        """Return all episodes for a given session."""
        return [ep for ep in self._episodes if ep.session_id == session_id]

    def get_recent(self, n: int = 10) -> list[Episode]:
        """Return the N most recent episodes."""
        return self._episodes[-n:]

    def get_by_time_range(self, start: float, end: float) -> list[Episode]:
        """Return episodes within a time range (Unix timestamps)."""
        return [ep for ep in self._episodes if start <= ep.timestamp <= end]
