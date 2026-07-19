"""LongTermMemory — adapter that wraps VectorMemory to implement MemoryBackend.

Uses lazy imports to avoid requiring qdrant-client/sentence-transformers
at import time. Falls back gracefully if dependencies are not installed.
"""

from __future__ import annotations

import uuid
from typing import Any

from aios.memory.backend import MemoryBackend, RetrievalResult


class LongTermMemory(MemoryBackend):
    """Vector-backed semantic memory using Qdrant + sentence-transformers.

    This is a thin adapter over the existing VectorMemory class, conforming
    to the MemoryBackend interface. If qdrant-client or sentence-transformers
    are not installed, operations raise ImportError with a helpful message.
    """

    def __init__(
        self,
        *,
        qdrant_url: str = "http://localhost:6333",
        collection: str = "aios_memory",
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        self._qdrant_url = qdrant_url
        self._collection = collection
        self._embedding_model = embedding_model
        self._backend: Any = None  # Lazy-initialized VectorMemory

    def _ensure_backend(self) -> Any:
        if self._backend is None:
            try:
                from aios.memory.vector_store import VectorMemory
            except ImportError as e:
                raise ImportError(
                    "LongTermMemory requires qdrant-client and sentence-transformers. "
                    "Install with: pip install qdrant-client sentence-transformers"
                ) from e

            self._backend = VectorMemory(
                qdrant_url=self._qdrant_url,
                collection=self._collection,
                embedding_model=self._embedding_model,
            )
        return self._backend

    async def store(self, content: str, *, metadata: dict[str, Any] | None = None) -> str:
        backend = self._ensure_backend()
        doc_id = uuid.uuid4().hex[:12]
        from aios.memory.vector_store import MemoryEntry

        entry = MemoryEntry(
            id=doc_id,
            text=content,
            namespace=metadata.pop("namespace", "default") if metadata else "default",
            metadata=metadata or {},
        )
        await backend.store(entry)
        return doc_id

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[RetrievalResult]:
        backend = self._ensure_backend()
        raw = await backend.search(query, limit=top_k)

        results = []
        for r in raw:
            score = r.get("score", 0.0)
            if score >= min_score:
                results.append(RetrievalResult(
                    content=r.get("text", ""),
                    score=score,
                    metadata={k: v for k, v in r.items() if k not in ("text", "score", "id")},
                    source="long_term",
                    doc_id=str(r.get("id", "")),
                ))
        return results

    async def delete(self, doc_id: str) -> bool:
        backend = self._ensure_backend()
        try:
            await backend.delete(doc_id)
            return True
        except Exception:
            return False

    async def clear(self) -> None:
        # VectorMemory doesn't have a clear method; skip for now
        pass

    async def count(self) -> int:
        # VectorMemory doesn't expose count; return 0 as placeholder
        return 0
