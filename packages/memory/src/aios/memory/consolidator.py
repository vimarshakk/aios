"""MemoryConsolidator — extracts facts from episodes and builds a knowledge graph."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from aios.memory.fact_store import Fact, FactStore

if TYPE_CHECKING:
    from aios.memory.episodic import Episode, EpisodicMemory
    from aios.memory.graph import KnowledgeGraph


@dataclass
class ConsolidationResult:
    """Summary of a consolidation run."""

    facts_extracted: int = 0
    facts_stored: int = 0
    facts_deduplicated: int = 0
    nodes_added: int = 0
    edges_added: int = 0


class MemoryConsolidator:
    """Extracts entity-relation-entity facts from episodic memories and
    stores them in a FactStore and KnowledgeGraph.

    M2.2 rule-based extraction handles simple patterns like:
      - "X works at Y"
      - "X is a Y"
      - "X knows Y"
      - "X mentioned Y"
      - "X likes Y"
      - "X is located in Y"

    Future: LLM-powered extraction for complex sentences.
    """

    _PATTERNS: ClassVar[list[tuple[str, int, str, int]]] = [
        (r"(.+?)\s+works?\s+at\s+(.+)", 1, "works_at", 2),
        (r"(.+?)\s+is\s+a\s+(.+)", 1, "is_a", 2),
        (r"(.+?)\s+knows?\s+(.+)", 1, "knows", 2),
        (r"(.+?)\s+mentioned?\s+(.+)", 1, "mentioned", 2),
        (r"(.+?)\s+likes?\s+(.+)", 1, "likes", 2),
        (r"(.+?)\s+is\s+located\s+in\s+(.+)", 1, "located_in", 2),
        (r"(.+?)\s+prefers?\s+(.+)", 1, "prefers", 2),
        (r"(.+?)\s+uses?\s+(.+)", 1, "uses", 2),
    ]

    def __init__(
        self,
        graph: KnowledgeGraph,
        fact_store: FactStore,
    ) -> None:
        self._graph = graph
        self._fact_store = fact_store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def consolidate_episode(self, episode: Episode) -> ConsolidationResult:
        """Extract facts from a single episode and store them."""
        result = ConsolidationResult()
        facts = self._extract_facts(episode.content)
        result.facts_extracted = len(facts)

        # Deduplicate against existing facts
        existing = await self._fact_store.list_all()
        deduped = self._deduplicate(facts, existing)
        result.facts_deduplicated = result.facts_extracted - len(deduped)

        # Store facts
        for fact in deduped:
            await self._fact_store.store(fact)
            result.facts_stored += 1

        # Import into graph
        nodes_before = self._graph.node_count()
        edges_before = self._graph.edge_count()
        self._graph.from_facts(deduped)
        result.nodes_added = self._graph.node_count() - nodes_before
        result.edges_added = self._graph.edge_count() - edges_before

        return result

    async def consolidate_batch(
        self, episodes: list[Episode]
    ) -> ConsolidationResult:
        """Consolidate multiple episodes into a single combined result."""
        combined = ConsolidationResult()
        for episode in episodes:
            r = await self.consolidate_episode(episode)
            combined.facts_extracted += r.facts_extracted
            combined.facts_stored += r.facts_stored
            combined.facts_deduplicated += r.facts_deduplicated
            combined.nodes_added += r.nodes_added
            combined.edges_added += r.edges_added
        return combined

    async def consolidate_all(
        self, episodic: EpisodicMemory
    ) -> ConsolidationResult:
        """Consolidate all episodes in an EpisodicMemory backend."""
        count = await episodic.count()
        episodes = episodic.get_recent(n=count)
        return await self.consolidate_batch(episodes)

    async def prune(self, min_confidence: float = 0.3) -> int:
        """Remove facts with confidence below threshold. Returns count removed."""
        all_facts = await self._fact_store.list_all()
        removed = 0
        for fact in all_facts:
            if fact.confidence < min_confidence:
                await self._fact_store.delete(fact.id)
                # Also remove from graph
                edge_id = f"fact:{fact.id}"
                self._graph.remove_edge(edge_id)
                removed += 1
        return removed

    # ------------------------------------------------------------------
    # Fact extraction (rule-based)
    # ------------------------------------------------------------------

    def _extract_facts(self, text: str) -> list[Fact]:
        """Extract entity-relation-entity triples from text."""
        facts: list[Fact] = []
        sentences = re.split(r"[.;!\n]+", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            for pattern, subj_g, predicate, obj_g in self._PATTERNS:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    subject = match.group(subj_g).strip()
                    obj = match.group(obj_g).strip()
                    # Clean up trailing punctuation
                    subject = subject.rstrip(".,;:!?")
                    obj = obj.rstrip(".,;:!?")
                    if subject and obj and subject.lower() != obj.lower():
                        fact = Fact(
                            id=uuid.uuid4().hex[:12],
                            subject=subject,
                            predicate=predicate,
                            obj=obj,
                            confidence=0.8,
                            source="consolidation",
                        )
                        facts.append(fact)
                    break  # One match per sentence

        return facts

    def _deduplicate(
        self,
        new_facts: list[Fact],
        existing_facts: list[Fact],
    ) -> list[Fact]:
        """Deduplicate new facts against existing and within new facts.

        Merges duplicates, keeping the highest confidence version.
        Returns facts to store (new or updated with higher confidence).
        """
        # Index existing facts by normalized key
        existing_map: dict[tuple[str, str, str], Fact] = {}
        for fact in existing_facts:
            key = (fact.subject.lower(), fact.predicate.lower(), fact.obj.lower())
            existing_map[key] = fact

        # Merge within new facts and against existing
        merged: dict[tuple[str, str, str], Fact] = {}
        for fact in new_facts:
            key = (fact.subject.lower(), fact.predicate.lower(), fact.obj.lower())
            if key in merged:
                if fact.confidence > merged[key].confidence:
                    merged[key] = fact
            else:
                merged[key] = fact

        # Filter: keep only truly new or updated (higher confidence than existing)
        deduped: list[Fact] = []
        for key, fact in merged.items():
            existing = existing_map.get(key)
            if existing is None or fact.confidence > existing.confidence:
                deduped.append(fact)

        return deduped


__all__ = [
    "ConsolidationResult",
    "MemoryConsolidator",
]
