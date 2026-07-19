"""MemoryRetriever — semantic search across memory backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class Searchable(Protocol):
    """Protocol for any memory backend that supports semantic search."""

    async def search(self, query: str, *, top_k: int = 5) -> list[MemoryHit]: ...


@dataclass
class MemoryHit:
    """A single hit from a memory backend search."""

    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = ""


@dataclass
class RetrievalResult:
    """Normalized retrieval result from any memory backend."""

    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = ""


class MemoryRetriever:
    """Retrieve relevant context from one or more memory backends.

    Wraps any object implementing the Searchable protocol (VectorMemory,
    FactStore wrappers, etc.) and normalizes results into RetrievalResult.
    """

    def __init__(self, backends: list[Any] | None = None) -> None:
        self._backends: list[Any] = backends or []

    def add_backend(self, backend: Any) -> None:
        """Register a memory backend for retrieval."""
        self._backends.append(backend)

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[RetrievalResult]:
        """Search all registered backends and merge results.

        Returns the top_k results across all backends, sorted by score descending.
        """
        all_hits: list[RetrievalResult] = []

        for backend in self._backends:
            if not hasattr(backend, "search"):
                continue

            try:
                hits = await backend.search(query, top_k=top_k)
                all_hits.extend(
                    RetrievalResult(
                        content=hit.text,
                        score=hit.score,
                        metadata=hit.metadata,
                        source=getattr(backend, "__class__", type(backend)).__name__,
                    )
                    for hit in hits
                )
            except Exception:  # noqa: S112
                # Backend errors should not crash retrieval
                continue

        # Sort by score descending
        all_hits.sort(key=lambda h: h.score, reverse=True)

        # Filter by minimum score
        if min_score > 0:
            all_hits = [h for h in all_hits if h.score >= min_score]

        return all_hits[:top_k]
