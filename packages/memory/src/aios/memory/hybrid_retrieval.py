"""HybridRetrieval — unified retrieval from multiple memory backends.

Combines results from:
1. Semantic vector search (TF-IDF cosine similarity)
2. Knowledge graph traversal (neighborhood + path-based)
3. Keyword search (exact + fuzzy substring matching)
4. Recency scoring (exponential decay)
5. Importance scoring (content-based heuristics)

Returns a unified ranked result set with source attribution.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from aios.memory.entity import EntityMemory
from aios.memory.episodic import EpisodicMemory
from aios.memory.graph import KnowledgeGraph
from aios.memory.vector_light import LightweightVectorMemory


@dataclass
class HybridResult:
    """A single result from hybrid retrieval."""

    id: str
    content: str
    source: str  # "vector", "graph", "keyword", "entity", "episodic"
    vector_score: float = 0.0
    graph_score: float = 0.0
    keyword_score: float = 0.0
    recency_score: float = 0.0
    importance_score: float = 0.0
    final_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0

    def __post_init__(self) -> None:
        # Weighted combination
        self.final_score = (
            0.30 * self.vector_score
            + 0.25 * self.graph_score
            + 0.20 * self.keyword_score
            + 0.15 * self.recency_score
            + 0.10 * self.importance_score
        )


@dataclass
class HybridRetrievalConfig:
    """Configuration for hybrid retrieval."""

    vector_weight: float = 0.30
    graph_weight: float = 0.25
    keyword_weight: float = 0.20
    recency_weight: float = 0.15
    importance_weight: float = 0.10
    max_results: int = 20
    vector_top_k: int = 30
    graph_depth: int = 2
    deduplicate: bool = True


class HybridRetrieval:
    """Unified retrieval engine combining vector, graph, keyword, and recency.

    Usage:
        hr = HybridRetrieval(
            vector_memory=vector_mem,
            graph=kg,
            episodic=ep_mem,
            entity_memory=ent_mem,
        )
        results = await hr.search("project architecture", top_k=10)
    """

    def __init__(
        self,
        vector_memory: LightweightVectorMemory,
        graph: KnowledgeGraph,
        episodic: EpisodicMemory | None = None,
        entity_memory: EntityMemory | None = None,
        config: HybridRetrievalConfig | None = None,
    ) -> None:
        self._vector = vector_memory
        self._graph = graph
        self._episodic = episodic
        self._entity = entity_memory
        self._config = config or HybridRetrievalConfig()

    async def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        sources: list[str] | None = None,
    ) -> list[HybridResult]:
        """Run hybrid retrieval across all backends.

        Args:
            query: Search query.
            top_k: Max results (overrides config).
            sources: Limit to specific sources ["vector", "graph", "keyword", "entity", "episodic"].

        Returns:
            Ranked list of HybridResult.
        """
        top_k = top_k or self._config.max_results
        active_sources = sources or ["vector", "graph", "keyword", "entity", "episodic"]
        now = time.time()

        # Collect candidates from each source
        candidates: dict[str, HybridResult] = {}

        # 1. Vector search
        if "vector" in active_sources:
            self._search_vector(query, candidates)

        # 2. Graph traversal
        if "graph" in active_sources:
            self._search_graph(query, candidates)

        # 3. Keyword search
        if "keyword" in active_sources:
            self._search_keyword(query, candidates)

        # 4. Entity search
        if "entity" in active_sources:
            await self._search_entity(query, candidates)

        # 5. Episodic search
        if "episodic" in active_sources:
            await self._search_episodic(query, candidates)

        # Score recency and importance for all candidates
        for result in candidates.values():
            result.recency_score = self._score_recency(result.created_at, now)
            result.importance_score = self._score_importance(result.content)

        # Deduplicate
        if self._config.deduplicate:
            candidates = self._deduplicate(candidates)

        # Sort by final_score
        ranked = sorted(candidates.values(), key=lambda r: r.final_score, reverse=True)
        return ranked[:top_k]

    # ------------------------------------------------------------------
    # Source-specific search
    # ------------------------------------------------------------------

    def _search_vector(
        self,
        query: str,
        candidates: dict[str, HybridResult],
    ) -> None:
        """Search vector memory with TF-IDF."""
        results = self._vector.search(query, top_k=self._config.vector_top_k)
        for r in results:
            if r.doc_id not in candidates:
                candidates[r.doc_id] = HybridResult(
                    id=r.doc_id,
                    content=r.content,
                    source="vector",
                    vector_score=r.score,
                    metadata=r.metadata,
                    created_at=r.created_at or 0.0,
                )
            else:
                candidates[r.doc_id].vector_score = max(
                    candidates[r.doc_id].vector_score, r.score
                )

    def _search_graph(
        self,
        query: str,
        candidates: dict[str, HybridResult],
    ) -> None:
        """Search knowledge graph via BFS from matching nodes."""
        query_words = set(query.lower().split())
        nodes = self._graph.list_nodes()

        # Find seed nodes matching query
        seed_ids: list[str] = []
        for node in nodes:
            node_words = set(node.label.lower().split())
            if query_words & node_words:
                seed_ids.append(node.id)

        # BFS from seed nodes
        visited: set[str] = set()
        for seed_id in seed_ids[:5]:  # limit seed breadth
            nodes_bfs = self._graph.bfs(seed_id, max_depth=self._config.graph_depth)
            for node in nodes_bfs:
                if node.id in visited:
                    continue
                visited.add(node.id)
                # Score based on distance from seed
                depth = self._graph.shortest_path_length(seed_id, node.id)
                score = max(0.1, 1.0 - (depth or 0) * 0.25)

                # Build content from node and its edges
                edges = self._graph.get_outgoing_edges(node.id)
                rels = [f"{e.relation}→{self._graph.get_node(e.target_id).label if self._graph.get_node(e.target_id) else '?'}" for e in edges[:5]]
                content = f"{node.label} ({node.node_type}): {'; '.join(rels)}" if rels else f"{node.label} ({node.node_type})"

                if node.id not in candidates:
                    candidates[node.id] = HybridResult(
                        id=node.id,
                        content=content,
                        source="graph",
                        graph_score=score,
                        metadata={"node_type": node.node_type, **node.properties},
                    )
                else:
                    candidates[node.id].graph_score = max(
                        candidates[node.id].graph_score, score
                    )

    def _search_keyword(
        self,
        query: str,
        candidates: dict[str, HybridResult],
    ) -> None:
        """Search via keyword matching across graph nodes."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for node in self._graph.list_nodes():
            label_lower = node.label.lower()
            # Exact match
            if query_lower in label_lower:
                score = 0.95
            else:
                node_words = set(label_lower.split())
                overlap = len(query_words & node_words)
                if overlap == 0:
                    continue
                score = min(0.8, 0.3 + 0.15 * overlap)

            if node.id not in candidates:
                candidates[node.id] = HybridResult(
                    id=node.id,
                    content=node.label,
                    source="keyword",
                    keyword_score=score,
                )
            else:
                candidates[node.id].keyword_score = max(
                    candidates[node.id].keyword_score, score
                )

    async def _search_entity(
        self,
        query: str,
        candidates: dict[str, HybridResult],
    ) -> None:
        """Search entity memory."""
        if self._entity is None:
            return
        results = await self._entity.retrieve(query, top_k=10)
        for r in results:
            if r.doc_id not in candidates:
                candidates[r.doc_id] = HybridResult(
                    id=r.doc_id,
                    content=r.content,
                    source="entity",
                    keyword_score=r.score,
                    metadata=r.metadata,
                    created_at=r.created_at,
                )
            else:
                candidates[r.doc_id].keyword_score = max(
                    candidates[r.doc_id].keyword_score, r.score
                )

    async def _search_episodic(
        self,
        query: str,
        candidates: dict[str, HybridResult],
    ) -> None:
        """Search episodic memory."""
        if self._episodic is None:
            return
        results = await self._episodic.retrieve(query, top_k=10)
        for r in results:
            if r.doc_id not in candidates:
                candidates[r.doc_id] = HybridResult(
                    id=r.doc_id,
                    content=r.content,
                    source="episodic",
                    keyword_score=r.score,
                    metadata=r.metadata,
                    created_at=r.created_at,
                )
            else:
                candidates[r.doc_id].keyword_score = max(
                    candidates[r.doc_id].keyword_score, r.score
                )

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _score_recency(self, created_at: float, now: float) -> float:
        """Exponential decay: 1.0 for now, ~0 after 7 days."""
        if created_at <= 0:
            return 0.5  # unknown time = medium score
        hours_ago = (now - created_at) / 3600
        return max(0.0, math.exp(-hours_ago / 168))  # 168 hours = 7 days

    def _score_importance(self, content: str) -> float:
        """Heuristic importance from content signals."""
        content_lower = content.lower()
        score = 0.3
        action_words = {"completed", "deployed", "fixed", "resolved",
                        "approved", "merged", "shipped", "launched"}
        if any(w in content_lower for w in action_words):
            score += 0.3
        if "?" in content:
            score += 0.1
        if len(content) > 200:
            score += 0.15
        return min(1.0, score)

    def _deduplicate(
        self, candidates: dict[str, HybridResult]
    ) -> dict[str, HybridResult]:
        """Deduplicate by content similarity."""
        seen_content: dict[str, str] = {}
        deduped: dict[str, HybridResult] = {}

        for result_id, result in candidates.items():
            # Normalize content for dedup
            normalized = result.content.lower().strip()[:100]
            if normalized not in seen_content:
                seen_content[normalized] = result_id
                deduped[result_id] = result
            else:
                # Merge scores into existing
                existing = deduped[seen_content[normalized]]
                existing.vector_score = max(existing.vector_score, result.vector_score)
                existing.graph_score = max(existing.graph_score, result.graph_score)
                existing.keyword_score = max(existing.keyword_score, result.keyword_score)

        return deduped


__all__ = [
    "HybridResult",
    "HybridRetrieval",
    "HybridRetrievalConfig",
]
