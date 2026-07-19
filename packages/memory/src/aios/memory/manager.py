"""HybridMemoryManager — unified facade over all memory backends."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from aios.memory.events import MemoryEvent, memory_deleted, memory_queried, memory_stored

if TYPE_CHECKING:
    from collections.abc import Callable

    from aios.memory.backend import MemoryBackend, RetrievalResult


@dataclass
class BackendConfig:
    """Configuration for a registered memory backend."""

    name: str
    backend: MemoryBackend
    weight: float = 1.0  # Multiplier for score blending
    enabled: bool = True
    priority: int = 0  # Higher = queried first


class HybridMemoryManager:
    """Unified facade that queries all registered backends, merges, deduplicates,
    and returns a single ranked list of RetrievalResult.

    ContextBuilder talks to HybridMemoryManager, never to individual backends.

    Responsibilities:
    - Decide which backends to query (all enabled by default)
    - Merge results from all backends
    - Weight scores by backend importance
    - Deduplicate by content similarity
    - Return a single ranked list
    - Emit lifecycle events for observability
    """

    def __init__(self) -> None:
        self._backends: dict[str, BackendConfig] = {}
        self._event_handlers: list[Callable[[MemoryEvent], Any]] = []

    def register(
        self,
        name: str,
        backend: MemoryBackend,
        *,
        weight: float = 1.0,
        priority: int = 0,
    ) -> None:
        """Register a memory backend."""
        self._backends[name] = BackendConfig(
            name=name,
            backend=backend,
            weight=weight,
            priority=priority,
        )

    def unregister(self, name: str) -> bool:
        """Remove a backend by name."""
        return self._backends.pop(name, None) is not None

    def enable(self, name: str) -> None:
        """Enable a backend."""
        if name in self._backends:
            self._backends[name].enabled = True

    def disable(self, name: str) -> None:
        """Disable a backend."""
        if name in self._backends:
            self._backends[name].enabled = False

    def on_event(self, handler: Callable[[MemoryEvent], Any]) -> None:
        """Register an event handler for memory lifecycle events."""
        self._event_handlers.append(handler)

    def _emit(self, event: MemoryEvent) -> None:
        """Emit a memory event to all registered handlers."""
        for handler in self._event_handlers:
            with suppress(Exception):
                handler(event)

    def _deduplicate(self, results: list[RetrievalResult]) -> list[RetrievalResult]:
        """Remove near-duplicate results by content similarity."""
        if not results:
            return []

        seen: list[str] = []
        unique: list[RetrievalResult] = []

        for r in results:
            normalized = r.content.strip().lower()
            is_dup = False

            for s in seen:
                if normalized in s or s in normalized:
                    is_dup = True
                    break

            if not is_dup:
                seen.append(normalized)
                unique.append(r)

        return unique

    async def store(
        self,
        content: str,
        *,
        backend: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store content in a specific backend (or the first enabled one).

        Returns the document ID.
        """
        target = None
        if backend and backend in self._backends:
            target = self._backends[backend]
        else:
            for cfg in self._backends.values():
                if cfg.enabled:
                    target = cfg
                    break

        if not target:
            raise RuntimeError("No enabled memory backend available")

        doc_id = await target.backend.store(content, metadata=metadata or {})
        self._emit(memory_stored(target.name, doc_id, content))
        return doc_id

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.0,
        backends: list[str] | None = None,
    ) -> list[RetrievalResult]:
        """Query all (or specified) backends, merge, rank, and deduplicate."""
        targets = []
        if backends:
            targets = [
                self._backends[b]
                for b in backends
                if b in self._backends and self._backends[b].enabled
            ]
        else:
            targets = [cfg for cfg in self._backends.values() if cfg.enabled]

        if not targets:
            return []

        # Query all targets (sorted by priority descending)
        targets.sort(key=lambda t: t.priority, reverse=True)

        all_results: list[RetrievalResult] = []
        for target in targets:
            try:
                results = await target.backend.retrieve(
                    query, top_k=top_k, min_score=min_score
                )
                for r in results:
                    r.score *= target.weight
                    r.source = target.name
                all_results.extend(results)
                self._emit(memory_queried(target.name, query, len(results)))
            except Exception:  # noqa: S112
                continue

        all_results.sort(key=lambda r: r.score, reverse=True)
        deduplicated = self._deduplicate(all_results)
        final = deduplicated[:top_k]

        self._emit(memory_queried("hybrid", query, len(final)))
        return final

    async def delete(self, doc_id: str, *, backend: str | None = None) -> bool:
        """Delete a document from a specific or all backends."""
        deleted = False
        targets = (
            [self._backends[backend]]
            if backend and backend in self._backends
            else [cfg for cfg in self._backends.values() if cfg.enabled]
        )

        for target in targets:
            try:
                if await target.backend.delete(doc_id):
                    deleted = True
                    self._emit(memory_deleted(target.name, doc_id))
            except Exception:  # noqa: S112
                continue

        return deleted

    async def clear(self, *, backend: str | None = None) -> None:
        """Clear all (or specified) backends."""
        targets = (
            [self._backends[backend]]
            if backend and backend in self._backends
            else [cfg for cfg in self._backends.values() if cfg.enabled]
        )

        for target in targets:
            try:
                await target.backend.clear()
                self._emit(memory_deleted(target.name, "*"))
            except Exception:  # noqa: S112
                continue

    async def count(self) -> dict[str, int]:
        """Return document counts per backend."""
        counts: dict[str, int] = {}
        for name, cfg in self._backends.items():
            if cfg.enabled:
                try:
                    counts[name] = await cfg.backend.count()
                except Exception:
                    counts[name] = -1
        return counts

    def list_backends(self) -> list[str]:
        """Return names of all registered backends."""
        return list(self._backends.keys())

    def get_backend(self, name: str) -> MemoryBackend | None:
        """Get a backend by name."""
        cfg = self._backends.get(name)
        return cfg.backend if cfg else None

    async def close(self) -> None:
        """Close all backends."""
        for cfg in self._backends.values():
            with suppress(Exception):
                await cfg.backend.close()
