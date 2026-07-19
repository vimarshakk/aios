"""AIOS Vector Service — embedding storage and similarity search."""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger("aios.vector")


class VectorStore:
    """In-memory vector store for similarity search.

    Provides add/query/delete over float vectors with cosine similarity.
    """

    def __init__(self, dimension: int = 384) -> None:
        self._dimension = dimension
        self._vectors: dict[str, list[float]] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def count(self) -> int:
        return len(self._vectors)

    def add(
        self,
        id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a vector with optional metadata."""
        if len(vector) != self._dimension:
            raise ValueError(
                f"Expected dimension {self._dimension}, got {len(vector)}"
            )
        self._vectors[id] = vector
        self._metadata[id] = metadata or {}

    def query(
        self,
        vector: list[float],
        *,
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Find the most similar vectors by cosine similarity.

        Args:
            vector: Query vector.
            top_k: Number of results to return.
            threshold: Minimum similarity score.

        Returns:
            List of {id, score, metadata} dicts.
        """
        if len(vector) != self._dimension:
            raise ValueError(
                f"Expected dimension {self._dimension}, got {len(vector)}"
            )
        results: list[dict[str, Any]] = []
        q_norm = _norm(vector)
        for vid, v in self._vectors.items():
            score = _cosine_similarity(vector, v, q_norm)
            if score >= threshold:
                results.append({
                    "id": vid,
                    "score": score,
                    "metadata": self._metadata.get(vid, {}),
                })
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    def remove(self, id: str) -> bool:
        """Remove a vector. Returns True if removed."""
        if id in self._vectors:
            del self._vectors[id]
            self._metadata.pop(id, None)
            return True
        return False

    def clear(self) -> None:
        """Remove all vectors."""
        self._vectors.clear()
        self._metadata.clear()


def _norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _cosine_similarity(a: list[float], b: list[float], a_norm: float) -> float:
    b_norm = _norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (a_norm * b_norm)


class VectorService:
    """High-level vector service wrapping VectorStore instances."""

    def __init__(self) -> None:
        self._stores: dict[str, VectorStore] = {}
        self._ready = False

    async def initialize(self) -> None:
        """Initialize vector backends."""
        self._ready = True
        logger.info("Vector service initialized")

    def get_store(
        self, namespace: str = "default", dimension: int = 384
    ) -> VectorStore:
        """Get or create a namespaced vector store."""
        if namespace not in self._stores:
            self._stores[namespace] = VectorStore(dimension=dimension)
        return self._stores[namespace]

    async def close(self) -> None:
        """Shut down the vector service."""
        self._stores.clear()
        self._ready = False
        logger.info("Vector service closed")


_service: VectorService | None = None


def get_vector_service() -> VectorService:
    """Get the global vector service singleton."""
    global _service
    if _service is None:
        _service = VectorService()
    return _service
