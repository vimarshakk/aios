"""Vector memory backed by Qdrant for semantic retrieval.

Extracted from OpenJarvis memory/retriever patterns (Apache 2.0).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    VectorParams,
)
from sentence_transformers import SentenceTransformer

DEFAULT_COLLECTION = "aios_memory"
DEFAULT_MODEL = "all-MiniLM-L6-v2"


@dataclass
class MemoryEntry:
    """A single memory entry with its embedding metadata."""

    id: str
    text: str
    namespace: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorMemory:
    """Semantic vector memory using Qdrant + sentence-transformers.
    Falls back to a local in-memory store if Qdrant connection fails.
    """

    def __init__(
        self,
        *,
        qdrant_url: str = "http://localhost:6333",
        collection: str = DEFAULT_COLLECTION,
        embedding_model: str = DEFAULT_MODEL,
    ) -> None:
        self._collection = collection
        self._encoder = SentenceTransformer(embedding_model)
        self._use_fallback = False
        self._fallback_store: list[dict[str, Any]] = []

        try:
            self._client = QdrantClient(url=qdrant_url, timeout=5.0)
            self._ensure_collection()
        except Exception as e:
            import sys

            print(
                f"WARNING: Qdrant client connection failed: {e}. "
                "Falling back to in-memory vector store.",
                file=sys.stderr,
            )
            self._use_fallback = True

    def _ensure_collection(self) -> None:
        if self._use_fallback:
            return
        existing = [c.name for c in self._client.get_collections().collections]
        if self._collection not in existing:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._encoder.get_sentence_embedding_dimension(),
                    distance=Distance.COSINE,
                ),
            )

    async def store(self, entry: MemoryEntry) -> None:
        embedding = self._encoder.encode(entry.text).tolist()
        if self._use_fallback:
            self._fallback_store.append(
                {
                    "id": entry.id,
                    "vector": embedding,
                    "text": entry.text,
                    "namespace": entry.namespace,
                    **entry.metadata,
                }
            )
            return

        self._client.upsert(
            collection_name=self._collection,
            points=[
                {
                    "id": entry.id,
                    "vector": embedding,
                    "payload": {
                        "text": entry.text,
                        "namespace": entry.namespace,
                        **entry.metadata,
                    },
                }
            ],
        )

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        embedding = self._encoder.encode(query).tolist()
        if self._use_fallback:
            import math

            def dot(v1: list[float], v2: list[float]) -> float:
                return sum(x * y for x, y in zip(v1, v2, strict=False))

            def mag(v: list[float]) -> float:
                return math.sqrt(sum(x * x for x in v))

            def cos_sim(v1: list[float], v2: list[float]) -> float:
                m1, m2 = mag(v1), mag(v2)
                return dot(v1, v2) / (m1 * m2) if m1 and m2 else 0.0

            scored = []
            for item in self._fallback_store:
                if namespace and item.get("namespace") != namespace:
                    continue
                score = cos_sim(embedding, item["vector"])
                scored.append(
                    {
                        "id": item["id"],
                        "text": item["text"],
                        "score": score,
                        "namespace": item["namespace"],
                        **{
                            k: v
                            for k, v in item.items()
                            if k not in ("id", "vector", "text", "namespace")
                        },
                    }
                )
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:limit]

        query_filter = None
        if namespace:
            query_filter = Filter(
                must=[FieldCondition(key="namespace", match=MatchValue(value=namespace))]
            )
        results = self._client.search(
            collection_name=self._collection,
            query_vector=embedding,
            limit=limit,
            query_filter=query_filter,
        )
        return [
            {
                "id": r.id,
                "text": r.payload.get("text", ""),
                "score": r.score,
                "namespace": r.payload.get("namespace", "default"),
                **{k: v for k, v in r.payload.items() if k not in ("text", "namespace")},
            }
            for r in results
        ]

    async def delete(self, entry_id: str) -> None:
        if self._use_fallback:
            self._fallback_store = [x for x in self._fallback_store if x["id"] != entry_id]
            return

        self._client.delete(
            collection_name=self._collection,
            points_selector=PointIdsList(points=[entry_id]),
        )


__all__ = ["MemoryEntry", "VectorMemory"]
