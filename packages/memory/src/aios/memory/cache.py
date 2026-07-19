"""CacheMemory — LRU cache for frequently accessed memory queries."""

from __future__ import annotations

import time
import uuid
from collections import OrderedDict
from typing import Any

from aios.memory.backend import MemoryBackend, RetrievalResult


class CacheMemory(MemoryBackend):
    """LRU cache for frequently accessed memory entries.

    Wraps another MemoryBackend and caches query results. Useful for
    reducing latency on repeated queries (e.g., "what is my name"
    asked multiple times in a session).
    """

    def __init__(self, max_size: int = 100, ttl_seconds: float = 300.0) -> None:
        self._max_size = max_size
        self._ttl = ttl_seconds
        # LRU cache: query_key → (results, timestamp)
        self._cache: OrderedDict[str, tuple[list[RetrievalResult], float]] = OrderedDict()
        # Direct storage for cache-only entries
        self._entries: dict[str, tuple[str, dict[str, Any], float]] = {}

    def _make_key(self, query: str, top_k: int, min_score: float) -> str:
        return f"{query}|{top_k}|{min_score}"

    def _is_expired(self, timestamp: float) -> bool:
        return time.time() - timestamp > self._ttl

    def _evict_lru(self) -> None:
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    async def store(self, content: str, *, metadata: dict[str, Any] | None = None) -> str:
        doc_id = uuid.uuid4().hex[:12]
        self._entries[doc_id] = (content, metadata or {}, time.time())
        return doc_id

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[RetrievalResult]:
        key = self._make_key(query, top_k, min_score)

        # Check cache
        if key in self._cache:
            results, ts = self._cache[key]
            if not self._is_expired(ts):
                self._cache.move_to_end(key)
                return results
            # Expired — remove
            del self._cache[key]

        # Cache miss — do simple substring search on stored entries
        query_lower = query.lower()
        scored: list[tuple[float, str, dict[str, Any], float]] = []

        for (content, meta, created) in self._entries.values():
            content_lower = content.lower()
            if query_lower in content_lower:
                score = 0.8
            elif any(w in content_lower for w in query_lower.split()):
                score = 0.5
            else:
                score = 0.0

            if score >= min_score:
                scored.append((score, content, meta, created))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = [
            RetrievalResult(
                content=content,
                score=s,
                metadata=meta,
                source="cache",
                created_at=created,
            )
            for s, content, meta, created in scored[:top_k]
        ]

        # Store in cache
        self._cache[key] = (results, time.time())
        self._evict_lru()

        return results

    async def delete(self, doc_id: str) -> bool:
        if doc_id in self._entries:
            del self._entries[doc_id]
            return True
        return False

    async def clear(self) -> None:
        self._cache.clear()
        self._entries.clear()

    async def count(self) -> int:
        return len(self._entries)

    def invalidate(self, query: str | None = None) -> int:
        """Invalidate cached results.

        If query is provided, only invalidate entries matching that query.
        Otherwise, clear the entire cache.
        Returns the number of entries invalidated.
        """
        if query is None:
            count = len(self._cache)
            self._cache.clear()
            return count

        query_lower = query.lower()
        keys_to_remove = [
            k for k in self._cache
            if query_lower in k.split("|")[0].lower()
        ]
        for k in keys_to_remove:
            del self._cache[k]
        return len(keys_to_remove)

    async def has(self, doc_id: str) -> bool:
        return doc_id in self._entries
