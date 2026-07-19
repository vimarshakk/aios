"""MemoryBackend ABC — unified interface for all memory storage backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievalResult:
    """A single retrieval result from any memory backend."""

    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    doc_id: str = ""
    created_at: float | None = None


class MemoryBackend(ABC):
    """Abstract base class for all memory backends.

    Every memory implementation (short-term, long-term, episodic, entity, cache)
    conforms to this interface, allowing the ContextEngine to search across
    all backends uniformly.
    """

    @abstractmethod
    async def store(self, content: str, *, metadata: dict[str, Any] | None = None) -> str:
        """Store a piece of content in memory.

        Args:
            content: The text content to store.
            metadata: Optional metadata (tags, source, timestamp, etc.).

        Returns:
            The ID of the stored document.
        """
        ...

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[RetrievalResult]:
        """Retrieve content matching the query.

        Args:
            query: The search query.
            top_k: Maximum number of results to return.
            min_score: Minimum relevance score (0.0-1.0).

        Returns:
            List of retrieval results sorted by score descending.
        """
        ...

    @abstractmethod
    async def delete(self, doc_id: str) -> bool:
        """Delete a document by ID.

        Returns:
            True if the document was found and deleted.
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Remove all documents from this backend."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Return the number of stored documents."""
        ...

    async def has(self, doc_id: str) -> bool:  # noqa: ARG002
        """Check if a document exists."""
        return False

    async def close(self) -> None:  # noqa: B027
        """Release resources. Default is no-op."""
