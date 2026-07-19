"""Comprehensive tests for M2.2 — Knowledge Graph, Consolidator, GraphQuery."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from aios.memory.consolidator import MemoryConsolidator
from aios.memory.episodic import Episode, EpisodicMemory
from aios.memory.fact_store import Fact, JSONLFactStore
from aios.memory.graph import GraphEdge, GraphNode, KnowledgeGraph
from aios.memory.graph_query import GraphQuery

_store_counter = 0


def _make_store() -> JSONLFactStore:
    """Create a JSONLFactStore with a unique temp file."""
    global _store_counter
    _store_counter += 1
    path = Path(tempfile.gettempdir()) / f"test_facts_{_store_counter}.jsonl"
    path.unlink(missing_ok=True)
    return JSONLFactStore(str(path))

# ===================================================================
# KnowledgeGraph — node/edge CRUD
# ===================================================================


class TestGraphNodeEdge:
    def test_node_frozen(self) -> None:
        node = GraphNode(id="n1", label="Alice", node_type="entity")
        assert node.id == "n1"
        assert node.label == "Alice"
        assert node.node_type == "entity"
        assert node.properties == {}

    def test_node_with_properties(self) -> None:
        node = GraphNode(
            id="n1", label="X", node_type="concept", properties={"k": "v"}
        )
        assert node.properties["k"] == "v"

    def test_edge_frozen(self) -> None:
        edge = GraphEdge(id="e1", source_id="n1", target_id="n2", relation="knows")
        assert edge.source_id == "n1"
        assert edge.target_id == "n2"
        assert edge.relation == "knows"
        assert edge.weight == 1.0


class TestKnowledgeGraphCRUD:
    def test_add_node(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        assert g.node_count() == 1
        assert g.get_node("n1") is not None

    def test_add_edge(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        g.add_node(GraphNode(id="n2", label="B", node_type="entity"))
        ok = g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="r"))
        assert ok is True
        assert g.edge_count() == 1

    def test_add_edge_missing_node(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        ok = g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n99", relation="r"))
        assert ok is False
        assert g.edge_count() == 0

    def test_remove_node(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        g.add_node(GraphNode(id="n2", label="B", node_type="entity"))
        g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="r"))
        assert g.remove_node("n1") is True
        assert g.node_count() == 1
        assert g.edge_count() == 0

    def test_remove_nonexistent_node(self) -> None:
        g = KnowledgeGraph()
        assert g.remove_node("n99") is False

    def test_remove_edge(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        g.add_node(GraphNode(id="n2", label="B", node_type="entity"))
        g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="r"))
        assert g.remove_edge("e1") is True
        assert g.edge_count() == 0

    def test_get_edges_between(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        g.add_node(GraphNode(id="n2", label="B", node_type="entity"))
        g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="r1"))
        g.add_edge(GraphEdge(id="e2", source_id="n1", target_id="n2", relation="r2"))
        edges = g.get_edges_between("n1", "n2")
        assert len(edges) == 2

    def test_get_neighbors(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        g.add_node(GraphNode(id="n2", label="B", node_type="entity"))
        g.add_node(GraphNode(id="n3", label="C", node_type="entity"))
        g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="r"))
        g.add_edge(GraphEdge(id="e2", source_id="n1", target_id="n3", relation="r"))
        neighbors = g.get_neighbors("n1")
        assert len(neighbors) == 2
        neighbor_ids = {n.id for _, n in neighbors}
        assert neighbor_ids == {"n2", "n3"}

    def test_overwrite_node(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        g.add_node(GraphNode(id="n1", label="B", node_type="concept"))
        node = g.get_node("n1")
        assert node is not None
        assert node.label == "B"
        assert g.node_count() == 1


# ===================================================================
# KnowledgeGraph — traversal
# ===================================================================


class TestKnowledgeGraphTraversal:
    def test_bfs_linear(self) -> None:
        g = KnowledgeGraph()
        for i in range(4):
            g.add_node(GraphNode(id=f"n{i}", label=str(i), node_type="entity"))
        for i in range(3):
            g.add_edge(GraphEdge(id=f"e{i}", source_id=f"n{i}", target_id=f"n{i+1}", relation="r"))
        result = g.bfs("n0")
        assert [n.id for n in result] == ["n0", "n1", "n2", "n3"]

    def test_bfs_max_depth(self) -> None:
        g = KnowledgeGraph()
        for i in range(4):
            g.add_node(GraphNode(id=f"n{i}", label=str(i), node_type="entity"))
        for i in range(3):
            g.add_edge(GraphEdge(id=f"e{i}", source_id=f"n{i}", target_id=f"n{i+1}", relation="r"))
        result = g.bfs("n0", max_depth=1)
        assert [n.id for n in result] == ["n0", "n1"]

    def test_bfs_nonexistent_start(self) -> None:
        g = KnowledgeGraph()
        assert g.bfs("n99") == []

    def test_dfs_linear(self) -> None:
        g = KnowledgeGraph()
        for i in range(4):
            g.add_node(GraphNode(id=f"n{i}", label=str(i), node_type="entity"))
        for i in range(3):
            g.add_edge(GraphEdge(id=f"e{i}", source_id=f"n{i}", target_id=f"n{i+1}", relation="r"))
        result = g.dfs("n0")
        assert len(result) == 4
        assert result[0].id == "n0"

    def test_dfs_max_depth(self) -> None:
        g = KnowledgeGraph()
        for i in range(4):
            g.add_node(GraphNode(id=f"n{i}", label=str(i), node_type="entity"))
        for i in range(3):
            g.add_edge(GraphEdge(id=f"e{i}", source_id=f"n{i}", target_id=f"n{i+1}", relation="r"))
        result = g.dfs("n0", max_depth=0)
        assert len(result) == 1
        assert result[0].id == "n0"

    def test_bfs_diamond(self) -> None:
        g = KnowledgeGraph()
        for nid in ["a", "b", "c", "d"]:
            g.add_node(GraphNode(id=nid, label=nid, node_type="entity"))
        g.add_edge(GraphEdge(id="e1", source_id="a", target_id="b", relation="r"))
        g.add_edge(GraphEdge(id="e2", source_id="a", target_id="c", relation="r"))
        g.add_edge(GraphEdge(id="e3", source_id="b", target_id="d", relation="r"))
        g.add_edge(GraphEdge(id="e4", source_id="c", target_id="d", relation="r"))
        result = g.bfs("a")
        assert len(result) == 4
        # All nodes reachable
        assert {n.id for n in result} == {"a", "b", "c", "d"}


# ===================================================================
# KnowledgeGraph — shortest path
# ===================================================================


class TestKnowledgeGraphPath:
    def test_shortest_path_direct(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        g.add_node(GraphNode(id="n2", label="B", node_type="entity"))
        g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="r"))
        path = g.shortest_path("n1", "n2")
        assert path is not None
        assert [n.id for n in path] == ["n1", "n2"]

    def test_shortest_path_through(self) -> None:
        g = KnowledgeGraph()
        for nid in ["a", "b", "c"]:
            g.add_node(GraphNode(id=nid, label=nid, node_type="entity"))
        g.add_edge(GraphEdge(id="e1", source_id="a", target_id="b", relation="r"))
        g.add_edge(GraphEdge(id="e2", source_id="b", target_id="c", relation="r"))
        path = g.shortest_path("a", "c")
        assert path is not None
        assert [n.id for n in path] == ["a", "b", "c"]

    def test_shortest_path_same_node(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        path = g.shortest_path("n1", "n1")
        assert path is not None
        assert len(path) == 1

    def test_shortest_path_no_path(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        g.add_node(GraphNode(id="n2", label="B", node_type="entity"))
        path = g.shortest_path("n1", "n2")
        assert path is None

    def test_shortest_path_nonexistent_node(self) -> None:
        g = KnowledgeGraph()
        assert g.shortest_path("n99", "n99") is None


# ===================================================================
# KnowledgeGraph — analysis
# ===================================================================


class TestKnowledgeGraphAnalysis:
    def test_has_cycle_no(self) -> None:
        g = KnowledgeGraph()
        for i in range(3):
            g.add_node(GraphNode(id=f"n{i}", label=str(i), node_type="entity"))
        g.add_edge(GraphEdge(id="e1", source_id="n0", target_id="n1", relation="r"))
        g.add_edge(GraphEdge(id="e2", source_id="n1", target_id="n2", relation="r"))
        assert g.has_cycle() is False

    def test_has_cycle_yes(self) -> None:
        g = KnowledgeGraph()
        for i in range(3):
            g.add_node(GraphNode(id=f"n{i}", label=str(i), node_type="entity"))
        g.add_edge(GraphEdge(id="e1", source_id="n0", target_id="n1", relation="r"))
        g.add_edge(GraphEdge(id="e2", source_id="n1", target_id="n2", relation="r"))
        g.add_edge(GraphEdge(id="e3", source_id="n2", target_id="n0", relation="r"))
        assert g.has_cycle() is True

    def test_has_cycle_self_loop(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n1", relation="self"))
        assert g.has_cycle() is True

    def test_detect_communities_single(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        g.add_node(GraphNode(id="n2", label="B", node_type="entity"))
        g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="r"))
        communities = g.detect_communities()
        assert len(communities) == 1
        assert set(communities[0]) == {"n1", "n2"}

    def test_detect_communities_multiple(self) -> None:
        g = KnowledgeGraph()
        for nid in ["a", "b", "c", "d"]:
            g.add_node(GraphNode(id=nid, label=nid, node_type="entity"))
        g.add_edge(GraphEdge(id="e1", source_id="a", target_id="b", relation="r"))
        g.add_edge(GraphEdge(id="e2", source_id="c", target_id="d", relation="r"))
        communities = g.detect_communities()
        assert len(communities) == 2

    def test_detect_communities_isolated(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        g.add_node(GraphNode(id="n2", label="B", node_type="entity"))
        communities = g.detect_communities()
        assert len(communities) == 2


# ===================================================================
# KnowledgeGraph — from_facts
# ===================================================================


class TestKnowledgeGraphFromFacts:
    def test_from_facts_creates_nodes_and_edges(self) -> None:
        g = KnowledgeGraph()
        facts = [
            Fact(id="f1", subject="Alice", predicate="works_at", obj="Google"),
            Fact(id="f2", subject="Alice", predicate="knows", obj="Bob"),
        ]
        g.from_facts(facts)
        assert g.node_count() == 3  # Alice, Google, Bob
        assert g.edge_count() == 2

    def test_from_facts_deduplicates_nodes(self) -> None:
        g = KnowledgeGraph()
        facts = [
            Fact(id="f1", subject="Alice", predicate="works_at", obj="Google"),
            Fact(id="f2", subject="Alice", predicate="knows", obj="Bob"),
        ]
        g.from_facts(facts)
        # Alice should be one node, not two
        assert g.node_count() == 3

    def test_from_facts_empty(self) -> None:
        g = KnowledgeGraph()
        g.from_facts([])
        assert g.node_count() == 0
        assert g.edge_count() == 0


# ===================================================================
# MemoryConsolidator — fact extraction
# ===================================================================


class TestConsolidatorExtraction:
    def test_extract_works_at(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        facts = c._extract_facts("Alice works at Google")
        assert len(facts) == 1
        assert facts[0].subject == "Alice"
        assert facts[0].predicate == "works_at"
        assert facts[0].obj == "Google"

    def test_extract_is_a(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        facts = c._extract_facts("Bob is a doctor")
        assert len(facts) == 1
        assert facts[0].predicate == "is_a"

    def test_extract_knows(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        facts = c._extract_facts("Alice knows Bob")
        assert len(facts) == 1
        assert facts[0].predicate == "knows"

    def test_extract_multiple_sentences(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        facts = c._extract_facts(
            "Alice works at Google. Alice knows Bob. Bob is a doctor."
        )
        assert len(facts) == 3

    def test_extract_no_match(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        facts = c._extract_facts("The weather is nice today")
        assert len(facts) == 0

    def test_extract_ignores_self_reference(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        facts = c._extract_facts("Alice knows Alice")
        assert len(facts) == 0

    def test_extract_cleans_punctuation(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        facts = c._extract_facts("Alice works at Google.")
        assert len(facts) == 1
        assert facts[0].obj == "Google"


# ===================================================================
# MemoryConsolidator — deduplication
# ===================================================================


class TestConsolidatorDedup:
    def test_deduplicate_new_facts(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        new = [
            Fact(id="f1", subject="A", predicate="r", obj="B"),
            Fact(id="f2", subject="A", predicate="r", obj="B"),
        ]
        deduped = c._deduplicate(new, [])
        assert len(deduped) == 1

    def test_deduplicate_against_existing(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        existing = [Fact(id="f0", subject="A", predicate="r", obj="B")]
        new = [Fact(id="f1", subject="A", predicate="r", obj="B")]
        deduped = c._deduplicate(new, existing)
        assert len(deduped) == 0

    def test_deduplicate_keeps_different_predicates(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        new = [
            Fact(id="f1", subject="A", predicate="r1", obj="B"),
            Fact(id="f2", subject="A", predicate="r2", obj="B"),
        ]
        deduped = c._deduplicate(new, [])
        assert len(deduped) == 2

    def test_deduplicate_keeps_higher_confidence(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        existing = [
            Fact(id="f0", subject="A", predicate="r", obj="B", confidence=0.5)
        ]
        new = [
            Fact(id="f1", subject="A", predicate="r", obj="B", confidence=0.9)
        ]
        deduped = c._deduplicate(new, existing)
        assert len(deduped) == 1
        assert deduped[0].confidence == 0.9


# ===================================================================
# MemoryConsolidator — full pipeline
# ===================================================================


class TestConsolidatorPipeline:
    @pytest.mark.asyncio
    async def test_consolidate_episode(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        episode = Episode(
            id="ep1",
            content="Alice works at Google. Alice knows Bob.",
            timestamp=1000.0,
        )
        result = await c.consolidate_episode(episode)
        assert result.facts_extracted == 2
        assert result.facts_stored == 2
        assert g.node_count() == 3  # Alice, Google, Bob
        assert g.edge_count() == 2

    @pytest.mark.asyncio
    async def test_consolidate_deduplicates_across_episodes(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        ep1 = Episode(id="ep1", content="Alice works at Google.", timestamp=1000.0)
        ep2 = Episode(id="ep2", content="Alice works at Google.", timestamp=2000.0)
        r1 = await c.consolidate_episode(ep1)
        r2 = await c.consolidate_episode(ep2)
        assert r1.facts_stored == 1
        assert r2.facts_deduplicated == 1  # Second time, deduped against existing
        assert g.edge_count() == 1  # Only one edge

    @pytest.mark.asyncio
    async def test_consolidate_batch(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        episodes = [
            Episode(id="ep1", content="Alice works at Google.", timestamp=1000.0),
            Episode(id="ep2", content="Bob is a doctor.", timestamp=2000.0),
        ]
        result = await c.consolidate_batch(episodes)
        assert result.facts_extracted == 2
        assert result.facts_stored == 2
        assert g.node_count() == 4  # Alice, Google, Bob, doctor

    @pytest.mark.asyncio
    async def test_consolidate_all(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        episodic = EpisodicMemory()
        await episodic.store("Alice works at Google.", metadata={"timestamp": 1000.0})
        await episodic.store("Bob is a doctor.", metadata={"timestamp": 2000.0})
        result = await c.consolidate_all(episodic)
        assert result.facts_stored == 2
        assert g.node_count() == 4  # Alice, Google, Bob, doctor


# ===================================================================
# MemoryConsolidator — pruning
# ===================================================================


class TestConsolidatorPrune:
    @pytest.mark.asyncio
    async def test_prune_removes_low_confidence(self) -> None:
        g = KnowledgeGraph()
        store = _make_store()
        c = MemoryConsolidator(g, store)
        # Manually store facts with different confidences
        await store.store(Fact(
            id="f1", subject="A", predicate="r", obj="B", confidence=0.9
        ))
        await store.store(Fact(
            id="f2", subject="C", predicate="r", obj="D", confidence=0.1
        ))
        g.from_facts([
            Fact(id="f1", subject="A", predicate="r", obj="B", confidence=0.9),
            Fact(id="f2", subject="C", predicate="r", obj="D", confidence=0.1),
        ])
        removed = await c.prune(min_confidence=0.5)
        assert removed == 1
        remaining = await store.list_all()
        assert len(remaining) == 1
        assert remaining[0].id == "f1"


# ===================================================================
# GraphQuery
# ===================================================================


class TestGraphQuery:
    def _build_graph(self) -> KnowledgeGraph:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="Alice", node_type="entity"))
        g.add_node(GraphNode(id="n2", label="Google", node_type="entity"))
        g.add_node(GraphNode(id="n3", label="AI", node_type="concept"))
        g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="works_at"))
        g.add_edge(GraphEdge(id="e2", source_id="n1", target_id="n3", relation="likes"))
        return g

    def test_find_by_type(self) -> None:
        g = self._build_graph()
        q = GraphQuery(g)
        entities = q.find_by_type("entity")
        assert len(entities) == 2
        concepts = q.find_by_type("concept")
        assert len(concepts) == 1
        assert concepts[0].label == "AI"

    def test_find_by_relation(self) -> None:
        g = self._build_graph()
        q = GraphQuery(g)
        results = q.find_by_relation("works_at")
        assert len(results) == 1
        src, _edge, tgt = results[0]
        assert src.label == "Alice"
        assert tgt.label == "Google"

    def test_find_paths_direct(self) -> None:
        g = self._build_graph()
        q = GraphQuery(g)
        paths = q.find_paths("n1", "n2")
        assert len(paths) == 1
        assert [n.id for n in paths[0]] == ["n1", "n2"]

    def test_find_paths_no_path(self) -> None:
        g = self._build_graph()
        q = GraphQuery(g)
        paths = q.find_paths("n2", "n1")
        assert len(paths) == 0

    def test_find_paths_max_depth(self) -> None:
        g = KnowledgeGraph()
        for i in range(5):
            g.add_node(GraphNode(id=f"n{i}", label=str(i), node_type="entity"))
        for i in range(4):
            g.add_edge(GraphEdge(id=f"e{i}", source_id=f"n{i}", target_id=f"n{i+1}", relation="r"))
        q = GraphQuery(g)
        paths = q.find_paths("n0", "n4", max_depth=2)
        assert len(paths) == 0  # Too deep
        paths = q.find_paths("n0", "n4", max_depth=4)
        assert len(paths) == 1

    def test_neighborhood_depth_1(self) -> None:
        g = self._build_graph()
        q = GraphQuery(g)
        hood = q.neighborhood("n1", depth=1)
        assert len(hood["nodes"]) == 3  # Alice, Google, AI
        assert len(hood["edges"]) == 2

    def test_neighborhood_depth_0(self) -> None:
        g = self._build_graph()
        q = GraphQuery(g)
        hood = q.neighborhood("n1", depth=0)
        assert len(hood["nodes"]) == 1
        assert len(hood["edges"]) == 0

    def test_neighborhood_nonexistent(self) -> None:
        g = self._build_graph()
        q = GraphQuery(g)
        hood = q.neighborhood("n99")
        assert hood == {"nodes": [], "edges": []}

    def test_find_pattern(self) -> None:
        g = self._build_graph()
        q = GraphQuery(g)
        matches = q.find_pattern({"relation": "works_at"})
        assert len(matches) == 1
        assert matches[0].edges[0].relation == "works_at"

    def test_find_pattern_min_weight(self) -> None:
        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="entity"))
        g.add_node(GraphNode(id="n2", label="B", node_type="entity"))
        g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="r", weight=0.3))
        g.add_edge(GraphEdge(id="e2", source_id="n1", target_id="n2", relation="r2", weight=0.9))
        q = GraphQuery(g)
        matches = q.find_pattern({"min_weight": 0.5})
        assert len(matches) == 1

    def test_subgraph(self) -> None:
        g = self._build_graph()
        q = GraphQuery(g)
        sub = q.subgraph({"n1", "n2"})
        assert sub.node_count() == 2
        assert sub.edge_count() == 1  # Only n1→n2
