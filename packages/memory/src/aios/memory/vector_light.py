"""LightweightVectorMemory — zero-dependency semantic search using TF-IDF.

No Qdrant, no sentence-transformers, no numpy required. Uses pure Python
TF-IDF with cosine similarity for semantic search over stored documents.

For production with large corpora, swap to VectorMemory (Qdrant-backed).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchResult:
    """A single search result."""

    doc_id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


class LightweightVectorMemory:
    """In-memory vector store using TF-IDF + cosine similarity.

    Zero external dependencies. Good for up to ~100k documents.
    For larger scale, use VectorMemory (Qdrant) or pgvector.

    Usage:
        store = LightweightVectorMemory()
        await store.add("user prefers dark mode", {"user_id": "u1"})
        results = await store.search("dark theme", top_k=5)
    """

    def __init__(self) -> None:
        self._documents: dict[str, dict[str, Any]] = {}
        self._idf: dict[str, float] = {}
        self._doc_count = 0

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def add(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> str:
        """Add a document to the store.

        Args:
            content: Text content to index.
            metadata: Optional metadata (user_id, type, tags, etc.).
            doc_id: Optional explicit ID. Generated if not provided.

        Returns:
            The document ID.
        """
        doc_id = doc_id or str(uuid.uuid4())
        self._documents[doc_id] = {
            "content": content,
            "metadata": metadata or {},
            "tokens": self._tokenize(content),
        }
        self._doc_count += 1
        self._rebuild_idf()
        return doc_id

    def remove(self, doc_id: str) -> bool:
        """Remove a document. Returns True if removed."""
        if doc_id in self._documents:
            del self._documents[doc_id]
            self._doc_count -= 1
            self._rebuild_idf()
            return True
        return False

    def get(self, doc_id: str) -> dict[str, Any] | None:
        """Get a document by ID."""
        doc = self._documents.get(doc_id)
        if doc is None:
            return None
        return {
            "id": doc_id,
            "content": doc["content"],
            "metadata": doc["metadata"],
        }

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        threshold: float = 0.01,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Semantic search using TF-IDF cosine similarity.

        Args:
            query: Search query.
            top_k: Max results.
            threshold: Minimum similarity score.
            metadata_filter: Optional filter on metadata fields.

        Returns:
            List of SearchResult sorted by score descending.
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        query_tfidf = self._compute_tfidf(query_tokens)
        results: list[SearchResult] = []

        for doc_id, doc in self._documents.items():
            # Apply metadata filter
            if metadata_filter:
                if not all(
                    doc["metadata"].get(k) == v for k, v in metadata_filter.items()
                ):
                    continue

            doc_tfidf = self._compute_tfidf(doc["tokens"])
            score = self._cosine(query_tfidf, doc_tfidf)
            if score >= threshold:
                results.append(
                    SearchResult(
                        doc_id=doc_id,
                        content=doc["content"],
                        score=round(score, 4),
                        metadata=doc["metadata"],
                        created_at=doc["metadata"].get("created_at", ""),
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    @property
    def count(self) -> int:
        """Return the number of stored documents."""
        return len(self._documents)

    def clear(self) -> int:
        """Clear all documents. Returns count removed."""
        n = len(self._documents)
        self._documents.clear()
        self._idf.clear()
        self._doc_count = 0
        return n

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def export_all(self) -> list[dict[str, Any]]:
        """Export all documents as JSON-serializable list."""
        return [
            {
                "id": doc_id,
                "content": doc["content"],
                "metadata": doc["metadata"],
            }
            for doc_id, doc in self._documents.items()
        ]

    def import_episodes(self, data: list[dict[str, Any]]) -> int:
        """Import documents from list of {id, content, metadata?}. Returns count imported."""
        count = 0
        for item in data:
            doc_id = item.get("id", str(uuid.uuid4()))
            content = item.get("content")
            if not content:
                continue
            self.add(
                content=content,
                metadata=item.get("metadata", {}),
                doc_id=doc_id,
            )
            count += 1
        return count

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple whitespace + lowercase tokenization."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        return [t for t in text.split() if len(t) > 1]

    def _rebuild_idf(self) -> None:
        """Recompute IDF scores across all documents."""
        self._idf.clear()
        if self._doc_count == 0:
            return

        df: Counter[str] = Counter()
        for doc in self._documents.values():
            unique_tokens = set(doc["tokens"])
            for token in unique_tokens:
                df[token] += 1

        for token, freq in df.items():
            self._idf[token] = math.log((self._doc_count + 1) / (freq + 1)) + 1

    def _compute_tfidf(self, tokens: list[str]) -> dict[str, float]:
        """Compute TF-IDF vector for a list of tokens."""
        tf = Counter(tokens)
        total = len(tokens) if tokens else 1
        vec: dict[str, float] = {}
        for token, count in tf.items():
            idf = self._idf.get(token, 1.0)
            vec[token] = (count / total) * idf
        return vec

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        """Cosine similarity between two sparse vectors."""
        if not a or not b:
            return 0.0
        # Dot product
        dot = sum(a[k] * b[k] for k in a if k in b)
        # Magnitudes
        mag_a = math.sqrt(sum(v * v for v in a.values()))
        mag_b = math.sqrt(sum(v * v for v in b.values()))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)
