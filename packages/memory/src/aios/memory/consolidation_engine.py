"""ConsolidationEngine — background memory consolidation pipeline.

Periodically extracts entities, relationships, facts from episodic memories,
updates the Knowledge Graph, indexes into vector memory, scores importance,
and detects duplicates. Runs as an asyncio background task.

Pipeline:
    EpisodicMemory
        → Extract entities (rule-based + pattern matching)
        → Extract relationships (rule-based triples)
        → Deduplicate against existing facts
        → Score importance (recency × frequency × specificity)
        → Update Knowledge Graph (nodes + edges)
        → Index into Vector Memory (TF-IDF)
        → Link memories (cross-references)
        → Persist
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aios.memory.consolidator import ConsolidationResult, MemoryConsolidator
from aios.memory.entity import Entity, EntityMemory
from aios.memory.episodic import Episode
from aios.memory.fact_store import Fact, FactStore, JSONLFactStore
from aios.memory.graph import GraphEdge, GraphNode, KnowledgeGraph
from aios.memory.vector_light import LightweightVectorMemory

if TYPE_CHECKING:
    from aios.memory.episodic import EpisodicMemory

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Memory scoring
# ---------------------------------------------------------------------------

@dataclass
class MemoryScore:
    """Importance score for a memory."""

    doc_id: str
    content: str
    importance: float  # 0.0 – 1.0
    recency: float  # 0.0 – 1.0
    frequency: float  # 0.0 – 1.0
    specificity: float  # 0.0 – 1.0
    composite: float = 0.0  # weighted combination

    def __post_init__(self) -> None:
        self.composite = (
            0.35 * self.importance
            + 0.25 * self.recency
            + 0.20 * self.frequency
            + 0.20 * self.specificity
        )


# ---------------------------------------------------------------------------
# Consolidation metrics
# ---------------------------------------------------------------------------

@dataclass
class ConsolidationMetrics:
    """Metrics from a consolidation run."""

    episodes_processed: int = 0
    entities_extracted: int = 0
    relationships_extracted: int = 0
    facts_stored: int = 0
    facts_deduplicated: int = 0
    graph_nodes_added: int = 0
    graph_edges_added: int = 0
    vector_docs_indexed: int = 0
    memories_scored: int = 0
    duration_ms: float = 0.0
    last_run_at: float = 0.0
    run_count: int = 0
    errors: int = 0


# ---------------------------------------------------------------------------
# Entity / Relationship extraction
# ---------------------------------------------------------------------------

class EntityExtractor:
    """Extract entities and relationships from text using rule-based patterns."""

    # Simple entity patterns: capitalized words, quoted strings, @mentions
    _ENTITY_PATTERNS = [
        # Proper nouns (capitalized words)
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b",
        # Quoted strings
        r'"([^"]+)"',
        # @mentions
        r"@(\w+)",
    ]

    # Relationship patterns: subject-verb-object triples
    _RELATION_PATTERNS = [
        (r"(.+?)\s+works?\s+at\s+(.+)", "works_at"),
        (r"(.+?)\s+is\s+a\s+(.+)", "is_a"),
        (r"(.+?)\s+is\s+an\s+(.+)", "is_a"),
        (r"(.+?)\s+knows?\s+(.+)", "knows"),
        (r"(.+?)\s+mentioned?\s+(.+)", "mentioned"),
        (r"(.+?)\s+likes?\s+(.+)", "likes"),
        (r"(.+?)\s+dislikes?\s+(.+)", "dislikes"),
        (r"(.+?)\s+prefers?\s+(.+)", "prefers"),
        (r"(.+?)\s+uses?\s+(.+)", "uses"),
        (r"(.+?)\s+is\s+located\s+in\s+(.+)", "located_in"),
        (r"(.+?)\s+created\s+(.+)", "created"),
        (r"(.+?)\s+owns?\s+(.+)", "owns"),
        (r"(.+?)\s+manages?\s+(.+)", "manages"),
        (r"(.+?)\s+leads?\s+(.+)", "leads"),
        (r"(.+?)\s+sent\s+(.+)", "sent"),
        (r"(.+?)\s+received\s+(.+)", "received"),
        (r"(.+?)\s+discussed\s+(.+)", "discussed"),
        (r"(.+?)\s+planned\s+(.+)", "planned"),
        (r"(.+?)\s+reviewed\s+(.+)", "reviewed"),
        (r"(.+?)\s+approved\s+(.+)", "approved"),
        (r"(.+?)\s+rejected\s+(.+)", "rejected"),
    ]

    # Entity type heuristics
    _TYPE_HINTS = {
        "person": {"works", "knows", "likes", "sent", "received", "manages", "leads", "approved"},
        "place": {"located_in", "visited", "moved"},
        "thing": {"created", "owns", "uses", "built", "designed"},
        "concept": {"discussed", "planned", "reviewed", "rejected"},
        "document": {"created", "reviewed", "approved", "rejected", "sent", "received"},
        "project": {"created", "managed", "led", "planned"},
    }

    def extract_entities(self, text: str) -> list[dict[str, str]]:
        """Extract entity mentions from text.

        Returns list of {name, type} dicts.
        """
        import re

        entities: dict[str, dict[str, str]] = {}

        for pattern in self._ENTITY_PATTERNS:
            for match in re.finditer(pattern, text):
                name = match.group(1).strip()
                if len(name) < 2:
                    continue
                # Skip common words
                if name.lower() in {"the", "and", "for", "with", "this", "that", "was", "are", "has", "have", "had", "not", "but", "can", "will", "from", "they", "been", "their", "said", "each", "which", "there", "what", "when", "who", "how", "its", "may", "new", "now", "old", "see", "way", "who", "boy", "did", "got", "let", "say", "she", "too", "use"}:
                    continue
                if name not in entities:
                    entities[name] = {"name": name, "type": "entity"}

        return list(entities.values())

    def extract_relationships(self, text: str) -> list[dict[str, str]]:
        """Extract subject-relationship-object triples from text.

        Returns list of {subject, predicate, object} dicts.
        """
        import re

        relationships: list[dict[str, str]] = []
        sentences = re.split(r"[.;!\n]+", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            for pattern, predicate in self._RELATION_PATTERNS:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    subject = match.group(1).strip().rstrip(".,;:!?")
                    obj = match.group(2).strip().rstrip(".,;:!?")
                    if subject and obj and subject.lower() != obj.lower():
                        relationships.append({
                            "subject": subject,
                            "predicate": predicate,
                            "object": obj,
                        })
                    break  # One match per sentence

        return relationships


# ---------------------------------------------------------------------------
# ConsolidationEngine
# ---------------------------------------------------------------------------

class ConsolidationEngine:
    """Background memory consolidation engine.

    Coordinates:
    - Entity extraction from episodic memories
    - Relationship extraction
    - Fact deduplication
    - Memory importance scoring
    - Knowledge Graph updates
    - Vector memory indexing
    - Background scheduling with configurable interval
    """

    def __init__(
        self,
        episodic: EpisodicMemory,
        graph: KnowledgeGraph,
        fact_store: FactStore,
        vector_memory: LightweightVectorMemory,
        entity_memory: EntityMemory | None = None,
        interval_seconds: float = 60.0,
    ) -> None:
        self._episodic = episodic
        self._graph = graph
        self._fact_store = fact_store
        self._vector_memory = vector_memory
        self._entity_memory = entity_memory or EntityMemory()
        self._interval = interval_seconds
        self._entity_extractor = EntityExtractor()
        self._consolidator = MemoryConsolidator(graph, fact_store)
        self._metrics = ConsolidationMetrics()
        self._task: asyncio.Task[None] | None = None
        self._last_consolidated_id: str | None = None
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background consolidation task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "ConsolidationEngine started (interval=%.0fs)", self._interval
        )

    async def stop(self) -> None:
        """Stop the background consolidation task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ConsolidationEngine stopped")

    async def _run_loop(self) -> None:
        """Background loop that consolidates periodically."""
        while self._running:
            try:
                await self.consolidate()
            except Exception as exc:
                self._metrics.errors += 1
                logger.error("Consolidation error: %s", exc)
            await asyncio.sleep(self._interval)

    # ------------------------------------------------------------------
    # Manual trigger
    # ------------------------------------------------------------------

    async def consolidate(self) -> ConsolidationMetrics:
        """Run one consolidation pass. Can be called manually or by background loop.

        Returns metrics from this run.
        """
        start = time.time()
        run_metrics = ConsolidationMetrics()

        try:
            # Get unprocessed episodes
            all_episodes = self._episodic.get_recent(n=1000)
            if not all_episodes:
                run_metrics.duration_ms = (time.time() - start) * 1000
                return run_metrics

            # Find new episodes (after last consolidated)
            new_episodes = self._find_new_episodes(all_episodes)
            if not new_episodes:
                run_metrics.duration_ms = (time.time() - start) * 1000
                return run_metrics

            run_metrics.episodes_processed = len(new_episodes)

            # Step 1: Extract entities and relationships
            for episode in new_episodes:
                entities = self._entity_extractor.extract_entities(episode.content)
                relationships = self._entity_extractor.extract_relationships(episode.content)

                run_metrics.entities_extracted += len(entities)
                run_metrics.relationships_extracted += len(relationships)

                # Store entities
                for ent in entities:
                    await self._entity_memory.store(
                        ent["name"],
                        metadata={
                            "entity_name": ent["name"],
                            "entity_type": ent.get("type", "entity"),
                            "source_episode": episode.id,
                        },
                    )

                # Add relationships to entities
                for rel in relationships:
                    entity = self._entity_memory.get_entity_by_name(rel["subject"])
                    if entity:
                        self._entity_memory.add_relationship(
                            entity.id, rel["predicate"], rel["object"]
                        )

            # Step 2: Consolidate facts via existing consolidator
            consolidation_result = await self._consolidator.consolidate_batch(
                new_episodes
            )
            run_metrics.facts_stored = consolidation_result.facts_stored
            run_metrics.facts_deduplicated = consolidation_result.facts_deduplicated
            run_metrics.graph_nodes_added = consolidation_result.nodes_added
            run_metrics.graph_edges_added = consolidation_result.edges_added

            # Step 3: Index all episodes into vector memory
            for episode in new_episodes:
                doc_id = f"ep:{episode.id}"
                self._vector_memory.add(
                    content=episode.content,
                    metadata={
                        "episode_id": episode.id,
                        "session_id": episode.session_id,
                        "timestamp": episode.timestamp,
                        "tags": episode.tags,
                        "source": "consolidation",
                    },
                    doc_id=doc_id,
                )
                run_metrics.vector_docs_indexed += 1

            # Step 4: Index facts into vector memory
            all_facts = await self._fact_store.list_all()
            for fact in all_facts:
                doc_id = f"fact:{fact.id}"
                content = f"{fact.subject} {fact.predicate} {fact.obj}"
                self._vector_memory.add(
                    content=content,
                    metadata={
                        "fact_id": fact.id,
                        "subject": fact.subject,
                        "predicate": fact.predicate,
                        "object": fact.obj,
                        "confidence": fact.confidence,
                        "source": "fact_extraction",
                    },
                    doc_id=doc_id,
                )
                run_metrics.vector_docs_indexed += 1

            # Step 5: Score memories
            scored = self._score_memories(new_episodes, all_facts)
            run_metrics.memories_scored = len(scored)

            # Track last processed
            self._last_consolidated_id = new_episodes[-1].id

        except Exception as exc:
            run_metrics.errors += 1
            logger.error("Consolidation pipeline error: %s", exc)

        # Finalize metrics
        run_metrics.duration_ms = (time.time() - start) * 1000
        run_metrics.last_run_at = time.time()
        self._metrics = run_metrics
        self._metrics.run_count += 1

        logger.info(
            "Consolidation complete: %d episodes, %d facts, %d entities, "
            "%d vector docs, %.1fms",
            run_metrics.episodes_processed,
            run_metrics.facts_stored,
            run_metrics.entities_extracted,
            run_metrics.vector_docs_indexed,
            run_metrics.duration_ms,
        )

        return run_metrics

    # ------------------------------------------------------------------
    # Memory scoring
    # ------------------------------------------------------------------

    def _score_memories(
        self,
        episodes: list[Episode],
        facts: list[Fact],
    ) -> list[MemoryScore]:
        """Score memories by importance (recency × frequency × specificity)."""
        now = time.time()
        scored: list[MemoryScore] = []

        for episode in episodes:
            recency = self._compute_recency(episode.timestamp, now)
            frequency = self._compute_frequency(episode.content, episodes)
            specificity = self._compute_specificity(episode.content)
            importance = self._compute_importance(episode)

            score = MemoryScore(
                doc_id=episode.id,
                content=episode.content[:100],
                importance=importance,
                recency=recency,
                frequency=frequency,
                specificity=specificity,
            )
            scored.append(score)

        scored.sort(key=lambda s: s.composite, reverse=True)
        return scored

    def _compute_recency(self, timestamp: float, now: float) -> float:
        """Score recency: 1.0 for now, decays exponentially over time."""
        hours_ago = (now - timestamp) / 3600
        return max(0.0, 1.0 / (1.0 + hours_ago / 24.0))

    def _compute_frequency(
        self, content: str, episodes: list[Episode]
    ) -> float:
        """Score frequency: how often similar content appears."""
        words = set(content.lower().split())
        if not words:
            return 0.0
        match_count = 0
        for ep in episodes:
            ep_words = set(ep.content.lower().split())
            overlap = len(words & ep_words)
            if overlap > len(words) * 0.3:
                match_count += 1
        return min(1.0, match_count / max(len(episodes), 1) * 5)

    def _compute_specificity(self, content: str) -> float:
        """Score specificity: named entities, technical terms, unique words."""
        import re
        words = content.split()
        if not words:
            return 0.0
        # Named entities (capitalized)
        named = sum(1 for w in words if w[0].isupper() and len(w) > 1)
        # Quoted strings
        quoted = len(re.findall(r'"[^"]+"', content))
        # Unique word ratio
        unique_ratio = len(set(w.lower() for w in words)) / len(words)
        return min(1.0, (named * 0.15 + quoted * 0.2 + unique_ratio * 0.5))

    def _compute_importance(self, episode: Episode) -> float:
        """Score importance based on content signals."""
        content = episode.content.lower()
        score = 0.3  # base
        # Action verbs suggest importance
        action_words = {"completed", "finished", "deployed", "released", "fixed",
                        "resolved", "approved", "merged", "shipped", "launched"}
        if any(w in content for w in action_words):
            score += 0.3
        # Questions suggest learning/decision points
        if "?" in content:
            score += 0.1
        # Length suggests detail
        if len(content) > 200:
            score += 0.15
        # Tags suggest categorization
        if episode.tags:
            score += 0.15
        return min(1.0, score)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_new_episodes(self, episodes: list[Episode]) -> list[Episode]:
        """Find episodes newer than last consolidated."""
        if self._last_consolidated_id is None:
            return episodes
        for i, ep in enumerate(episodes):
            if ep.id == self._last_consolidated_id:
                return episodes[i + 1:]
        return episodes

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------

    def get_metrics(self) -> ConsolidationMetrics:
        """Get current consolidation metrics."""
        return self._metrics

    def get_entity_extractor(self) -> EntityExtractor:
        """Get the entity extractor for external use."""
        return self._entity_extractor

    def get_entity_memory(self) -> EntityMemory:
        """Get the entity memory store."""
        return self._entity_memory

    @property
    def is_running(self) -> bool:
        return self._running


__all__ = [
    "ConsolidationEngine",
    "ConsolidationMetrics",
    "EntityExtractor",
    "MemoryScore",
]
