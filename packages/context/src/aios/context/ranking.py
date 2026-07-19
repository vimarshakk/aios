"""RelevanceRanker — score and filter retrieved context by relevance to query."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aios.context.retriever import RetrievalResult


@dataclass
class ScoredResult:
    """A retrieval result with a relevance score."""

    content: str
    score: float
    metadata: dict = field(default_factory=dict)
    source: str = ""

    @property
    def is_relevant(self) -> bool:
        return self.score >= 0.5


class RelevanceRanker:
    """Score and rank retrieved context items by relevance to the query.

    Uses a lightweight TF-based scoring approach (no external ML dependencies).
    For production, swap in a learned reranker or use the vector store scores directly.
    """

    def __init__(self, min_score: float = 0.5) -> None:
        self._min_score = min_score

    def _tokenize(self, text: str) -> list[str]:
        """Simple whitespace + lowercase tokenization."""
        return [w.lower() for w in re.findall(r"\w+", text)]

    def _score(self, query_tokens: list[str], doc_tokens: list[str]) -> float:
        """Compute overlap score between query and document tokens.

        Score = 2 * |intersection| / (|query| + |doc|)  (Dice coefficient).
        """
        if not query_tokens or not doc_tokens:
            return 0.0

        query_set = set(query_tokens)
        doc_set = set(doc_tokens)
        intersection = query_set & doc_set

        if not intersection:
            return 0.0

        return 2 * len(intersection) / (len(query_set) + len(doc_set))

    def rank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        *,
        min_score: float | None = None,
    ) -> list[ScoredResult]:
        """Score and rank candidates by relevance to query.

        If candidates already carry a `score` from vector search, this method
        merges that signal with the token-overlap score (weighted 0.7 vs 0.3).
        """
        threshold = min_score if min_score is not None else self._min_score
        query_tokens = self._tokenize(query)

        scored: list[ScoredResult] = []
        for c in candidates:
            doc_tokens = self._tokenize(c.content)
            overlap_score = self._score(query_tokens, doc_tokens)

            # Blend vector score (if present) with overlap score
            blended = 0.7 * c.score + 0.3 * overlap_score if c.score > 0 else overlap_score

            scored.append(ScoredResult(
                content=c.content,
                score=blended,
                metadata=c.metadata,
                source=c.source,
            ))

        scored.sort(key=lambda s: s.score, reverse=True)
        return [s for s in scored if s.score >= threshold]

    def filter_relevant(
        self,
        results: list[ScoredResult],
        top_k: int = 5,
    ) -> list[ScoredResult]:
        """Return top-k most relevant results."""
        return results[:top_k]
