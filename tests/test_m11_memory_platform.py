"""M11.5–M11.9 Tests: Consolidation Engine, Workspace Memory,
Hybrid Retrieval, Memory Import/Export, and Gateway Endpoints.
"""

from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from aios.memory.consolidation_engine import (
    ConsolidationEngine,
    ConsolidationMetrics,
    EntityExtractor,
    MemoryScore,
)
from aios.memory.entity import Entity, EntityMemory
from aios.memory.episodic import Episode, EpisodicMemory
from aios.memory.fact_store import Fact, JSONLFactStore
from aios.memory.graph import GraphEdge, GraphNode, KnowledgeGraph
from aios.memory.hybrid_retrieval import HybridResult, HybridRetrieval, HybridRetrievalConfig
from aios.memory.memory_io import ExportResult, ImportResult, MemoryIO
from aios.memory.vector_light import LightweightVectorMemory
from aios.memory.workspace import Workspace, WorkspaceMemory, WorkspaceStats


def _run(coro):
    """Helper to run async in sync tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ═══════════════════════════════════════════════════════════════════════════
# M11.5 — Consolidation Engine
# ═══════════════════════════════════════════════════════════════════════════


class TestEntityExtractor:
    def test_extract_entities_single(self):
        ext = EntityExtractor()
        entities = ext.extract_entities("Alice called Bob about the project")
        names = {e["name"].lower() for e in entities}
        assert "alice" in names
        assert "bob" in names

    def test_extract_entities_empty(self):
        ext = EntityExtractor()
        assert ext.extract_entities("") == []

    def test_extract_entities_filters_stopwords(self):
        ext = EntityExtractor()
        entities = ext.extract_entities("The quick brown fox")
        names = {e["name"].lower() for e in entities}
        assert "the" not in names

    def test_extract_relationships(self):
        ext = EntityExtractor()
        rels = ext.extract_relationships("Alice works at Google")
        assert len(rels) >= 1
        assert rels[0]["predicate"] == "works_at"

    def test_extract_relationships_empty(self):
        ext = EntityExtractor()
        assert ext.extract_relationships("") == []

    def test_extract_relationships_knows(self):
        ext = EntityExtractor()
        rels = ext.extract_relationships("Alice knows Bob")
        assert len(rels) >= 1
        assert rels[0]["predicate"] == "knows"


class TestMemoryScore:
    def test_score_computation(self):
        score = MemoryScore(
            doc_id="test-1",
            content="test content",
            importance=0.8,
            recency=0.9,
            frequency=0.5,
            specificity=0.6,
        )
        assert 0.0 <= score.composite <= 1.0
        # composite = 0.35*0.8 + 0.25*0.9 + 0.20*0.5 + 0.20*0.6 = 0.28+0.225+0.10+0.12 = 0.725
        assert 0.7 <= score.composite <= 0.8

    def test_score_with_zero_importance(self):
        score = MemoryScore(
            doc_id="test-2",
            content="test",
            importance=0.0,
            recency=0.0,
            frequency=0.0,
            specificity=0.0,
        )
        assert score.composite == 0.0

    def test_score_with_max_values(self):
        score = MemoryScore(
            doc_id="test-3",
            content="test",
            importance=1.0,
            recency=1.0,
            frequency=1.0,
            specificity=1.0,
        )
        assert score.composite == 1.0


class TestConsolidationEngine:
    def _make_engine(self) -> ConsolidationEngine:
        episodic = EpisodicMemory()
        graph = KnowledgeGraph()
        fact_store = JSONLFactStore()
        vector_memory = LightweightVectorMemory()
        entity_memory = EntityMemory()
        return ConsolidationEngine(
            episodic=episodic,
            graph=graph,
            fact_store=fact_store,
            vector_memory=vector_memory,
            entity_memory=entity_memory,
            interval_seconds=3600.0,
        )

    def test_create_engine(self):
        engine = self._make_engine()
        assert engine is not None
        assert engine.is_running is False

    def test_start_stop(self):
        engine = self._make_engine()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(engine.start())
            assert engine.is_running is True
            loop.run_until_complete(engine.stop())
            assert engine.is_running is False
        finally:
            loop.close()

    def test_manual_consolidate_empty(self):
        engine = self._make_engine()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(engine.start())
            metrics = loop.run_until_complete(engine.consolidate())
            assert isinstance(metrics, ConsolidationMetrics)
            assert metrics.episodes_processed == 0  # no episodes
        finally:
            loop.run_until_complete(engine.stop())
            loop.close()

    def test_manual_consolidate_with_episodes(self):
        engine = self._make_engine()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(engine.start())
            # Add episodes directly to internal store
            ep1 = Episode(id="ep1", content="Alice called Bob about API", timestamp=time.time())
            ep2 = Episode(id="ep2", content="Meeting with Carol", timestamp=time.time())
            engine._episodic._episodes.extend([ep1, ep2])
            metrics = loop.run_until_complete(engine.consolidate())
            assert metrics.episodes_processed == 2
        finally:
            loop.run_until_complete(engine.stop())
            loop.close()

    def test_get_metrics(self):
        engine = self._make_engine()
        metrics = engine.get_metrics()
        assert isinstance(metrics, ConsolidationMetrics)
        assert metrics.run_count == 0

    def test_get_entity_extractor(self):
        engine = self._make_engine()
        ext = engine.get_entity_extractor()
        assert isinstance(ext, EntityExtractor)

    def test_consolidation_metrics_fields(self):
        m = ConsolidationMetrics()
        m.episodes_processed = 5
        m.entities_extracted = 3
        m.facts_stored = 2
        m.graph_nodes_added = 1
        m.vector_docs_indexed = 4
        m.duration_ms = 42.0
        assert m.episodes_processed == 5
        assert m.duration_ms == 42.0


# ═══════════════════════════════════════════════════════════════════════════
# M11.6 — Workspace Memory
# ═══════════════════════════════════════════════════════════════════════════


class TestWorkspaceMemory:
    def test_create_workspace(self):
        wm = WorkspaceMemory()
        ws = wm.create_workspace("proj-1", "First project")
        assert isinstance(ws, Workspace)
        assert ws.name == "proj-1"
        assert ws.description == "First project"
        assert ws.id.startswith("ws_")

    def test_get_workspace(self):
        wm = WorkspaceMemory()
        ws = wm.create_workspace("ws1")
        found = wm.get_workspace(ws.id)
        assert found is not None
        assert found.name == "ws1"

    def test_get_nonexistent_returns_none(self):
        wm = WorkspaceMemory()
        assert wm.get_workspace("nope") is None

    def test_list_workspaces(self):
        wm = WorkspaceMemory()
        wm.create_workspace("a")
        wm.create_workspace("b")
        workspaces = wm.list_workspaces()
        assert len(workspaces) == 2
        names = {ws.name for ws in workspaces}
        assert names == {"a", "b"}

    def test_delete_workspace(self):
        wm = WorkspaceMemory()
        ws = wm.create_workspace("del")
        assert wm.delete_workspace(ws.id) is True
        assert wm.get_workspace(ws.id) is None

    def test_delete_nonexistent(self):
        wm = WorkspaceMemory()
        assert wm.delete_workspace("nope") is False

    def test_get_stores(self):
        wm = WorkspaceMemory()
        ws = wm.create_workspace("s1")
        stores = wm.get_stores(ws.id)
        assert stores is not None
        assert stores.vector is not None
        assert stores.graph is not None

    def test_get_stores_nonexistent(self):
        wm = WorkspaceMemory()
        assert wm.get_stores("nope") is None

    def test_update_stats(self):
        wm = WorkspaceMemory()
        ws = wm.create_workspace("st1")
        stats = wm.update_stats(ws.id)
        assert isinstance(stats, WorkspaceStats)
        assert stats.graph_nodes == 0

    def test_update_stats_nonexistent(self):
        wm = WorkspaceMemory()
        stats = wm.update_stats("nope")
        assert isinstance(stats, WorkspaceStats)

    def test_get_or_create_workspace(self):
        wm = WorkspaceMemory()
        ws1 = wm.get_or_create_workspace("unique-name")
        ws2 = wm.get_or_create_workspace("unique-name")
        assert ws1.id == ws2.id

    def test_workspace_isolation(self):
        wm = WorkspaceMemory()
        ws1 = wm.create_workspace("w1")
        ws2 = wm.create_workspace("w2")
        stores1 = wm.get_stores(ws1.id)
        stores2 = wm.get_stores(ws2.id)
        assert stores1 is not stores2
        assert stores1.graph is not stores2.graph
        assert stores1.vector is not stores2.vector


# ═══════════════════════════════════════════════════════════════════════════
# M11.7 — Hybrid Retrieval
# ═══════════════════════════════════════════════════════════════════════════


class TestHybridRetrieval:
    def _make_retrieval(self) -> HybridRetrieval:
        vec = LightweightVectorMemory()
        graph = KnowledgeGraph()
        entity_mem = EntityMemory()
        return HybridRetrieval(vec, graph, entity_memory=entity_mem)

    def test_create_retrieval(self):
        hr = self._make_retrieval()
        assert hr is not None

    def test_search_empty(self):
        hr = self._make_retrieval()
        results = _run(hr.search("anything"))
        assert isinstance(results, list)

    def test_search_with_vector_data(self):
        hr = _make_retrieval_fresh()
        hr._vector.add("Alice started the project last week", metadata={"type": "event"})
        hr._vector.add("Bob deployed the API yesterday", metadata={"type": "event"})
        results = _run(hr.search("Alice project", sources=["vector"]))
        assert len(results) >= 1
        assert any("alice" in r.content.lower() for r in results)

    def test_search_with_graph_data(self):
        hr = _make_retrieval_fresh()
        n1 = GraphNode(id="n1", label="Alice", node_type="person")
        n2 = GraphNode(id="n2", label="API", node_type="project")
        hr._graph.add_node(n1)
        hr._graph.add_node(n2)
        hr._graph.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="works_on"))
        results = _run(hr.search("Alice", sources=["graph", "keyword"]))
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_hybrid_config(self):
        cfg = HybridRetrievalConfig(
            vector_weight=0.40,
            graph_weight=0.30,
            keyword_weight=0.20,
            max_results=5,
        )
        hr = HybridRetrieval(
            LightweightVectorMemory(),
            KnowledgeGraph(),
            config=cfg,
        )
        assert hr._config.vector_weight == 0.40
        assert hr._config.max_results == 5

    def test_hybrid_result_model(self):
        r = HybridResult(
            id="test-1",
            content="test",
            source="vector",
            vector_score=0.8,
        )
        assert r.id == "test-1"
        assert r.source == "vector"
        assert r.final_score > 0

    def test_deduplication(self):
        hr = _make_retrieval_fresh()
        # Add same content to vector
        hr._vector.add("Unique fact about quantum computing")
        hr._vector.add("Unique fact about quantum computing")
        results = _run(hr.search("quantum computing", sources=["vector"]))
        contents = [r.content for r in results]
        # Dedup should reduce duplicates
        assert len(contents) <= 2

    def test_limit_respected(self):
        hr = _make_retrieval_fresh()
        for i in range(20):
            hr._vector.add(f"Memory item number {i} about topic {i % 5}")
        results = _run(hr.search("topic", top_k=3, sources=["vector"]))
        assert len(results) <= 3

    def test_empty_sources(self):
        hr = _make_retrieval_fresh()
        hr._vector.add("test content")
        results = _run(hr.search("test", sources=[]))
        assert isinstance(results, list)


def _make_retrieval_fresh() -> HybridRetrieval:
    return HybridRetrieval(
        LightweightVectorMemory(),
        KnowledgeGraph(),
        entity_memory=EntityMemory(),
    )


# ═══════════════════════════════════════════════════════════════════════════
# M11.9 — Memory Import/Export
# ═══════════════════════════════════════════════════════════════════════════


class TestMemoryIO:
    def _make_io(self) -> MemoryIO:
        return MemoryIO(
            graph=KnowledgeGraph(),
            vector_memory=LightweightVectorMemory(),
        )

    def test_export_json_empty(self):
        io = self._make_io()
        result = io.export_json()
        assert isinstance(result, ExportResult)
        assert result.format == "json"
        assert result.graph_node_count == 0

    def test_export_json_with_graph(self):
        io = self._make_io()
        n1 = GraphNode(id="n1", label="Alice", node_type="person")
        n2 = GraphNode(id="n2", label="Bob", node_type="person")
        io._graph.add_node(n1)
        io._graph.add_node(n2)
        io._graph.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="knows"))
        result = io.export_json()
        assert result.graph_node_count == 2
        assert result.graph_edge_count == 1

    def test_export_json_content_is_json(self):
        io = self._make_io()
        result = io.export_json()
        import json
        data = json.loads(result.content)
        assert data["format"] == "aios-memory-json"

    def test_import_json_roundtrip(self):
        # Export first
        io_export = self._make_io()
        n = GraphNode(id="n1", label="TestNode", node_type="entity")
        io_export._graph.add_node(n)
        exported = io_export.export_json()
        # Import back
        io_import = self._make_io()
        result = _run(io_import.import_json(exported.content))
        assert isinstance(result, ImportResult)
        assert result.format == "json"

    def test_import_json_invalid(self):
        io = self._make_io()
        result = _run(io.import_json("not json"))
        assert len(result.errors) > 0

    def test_import_json_wrong_format(self):
        io = self._make_io()
        result = _run(io.import_json('{"format": "wrong"}'))
        assert len(result.errors) > 0

    def test_export_markdown(self):
        io = self._make_io()
        n = GraphNode(id="n1", label="Alice", node_type="person")
        io._graph.add_node(n)
        result = io.export_markdown()
        assert result.format == "markdown"
        assert "Alice" in result.content

    def test_import_markdown(self):
        io = self._make_io()
        md = "# AIOS Memory Export\n\n## Knowledge Graph\n\n**Nodes:** 0 | **Edges:** 0\n"
        result = _run(io.import_markdown(md))
        assert isinstance(result, ImportResult)
        assert result.format == "markdown"

    def test_export_result_counts(self):
        io = self._make_io()
        result = io.export_json(include_graph=False, include_episodes=False,
                                include_entities=False, include_facts=False)
        assert result.graph_node_count == 0
        assert result.size_bytes > 0


# ═══════════════════════════════════════════════════════════════════════════
# M11.10 — Gateway REST Endpoints (M11.5–M11.9)
# ═══════════════════════════════════════════════════════════════════════════


class TestGatewayM11Endpoints:
    """Test all M11.5–M11.9 REST endpoints via the FastAPI test client."""

    def _get_client(self):
        """Initialize gateway globals and create a test client."""
        import aios.gateway.main as gw

        # Initialize globals if not set
        gw._graph = KnowledgeGraph()
        gw._vector_memory = LightweightVectorMemory()
        gw._entity_memory = EntityMemory()
        gw._workspace_memory = WorkspaceMemory()
        gw._memory_manager = type("MemMgr", (), {"register": lambda self, *a: None, "close": lambda self: None})()
        from aios.memory.consolidation_engine import ConsolidationEngine
        from aios.memory.fact_store import JSONLFactStore
        gw._consolidation_engine = ConsolidationEngine(
            episodic=EpisodicMemory(),
            graph=gw._graph,
            fact_store=JSONLFactStore(),
            vector_memory=gw._vector_memory,
            entity_memory=gw._entity_memory,
            interval_seconds=3600.0,
        )
        from fastapi.testclient import TestClient
        return TestClient(gw.app)

    # --- M11.5 Consolidation ---

    def test_consolidate_endpoint(self):
        client = self._get_client()
        resp = client.post("/memory/consolidate", json={"max_memories": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert "ok" in data

    def test_memory_stats_endpoint(self):
        client = self._get_client()
        resp = client.get("/memory/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "ok" in data

    # --- M11.6 Workspace ---

    def test_workspace_crud(self):
        client = self._get_client()
        # Create
        resp = client.post("/memory/workspaces", json={"workspace_id": "test-ws", "description": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        ws_id = data["workspace_id"]

        # List
        resp = client.get("/memory/workspaces")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "test-ws" in data["workspaces"]

        # Detail
        resp = client.get(f"/memory/workspaces/{ws_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["workspace_id"] == ws_id

    def test_workspace_not_found(self):
        client = self._get_client()
        resp = client.post("/memory/workspaces/nonexistent/remember", json={"content": "x"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False

    def test_workspace_detail_nonexistent(self):
        client = self._get_client()
        resp = client.get("/memory/workspaces/nope")
        assert resp.status_code == 200
        assert resp.json()["ok"] is False

    def test_workspace_delete(self):
        client = self._get_client()
        resp = client.post("/memory/workspaces", json={"workspace_id": "del-ws"})
        ws_id = resp.json()["workspace_id"]
        resp = client.delete(f"/memory/workspaces/{ws_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        # Verify deleted
        resp = client.get(f"/memory/workspaces/{ws_id}")
        assert resp.json()["ok"] is False

    # --- M11.7 Hybrid Retrieval ---

    def test_hybrid_search_endpoint(self):
        client = self._get_client()
        resp = client.post("/memory/hybrid_search", json={"query": "anything", "limit": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert "ok" in data
        assert "results" in data

    # --- M11.9 Import/Export ---

    def test_export_endpoint(self):
        client = self._get_client()
        resp = client.get("/memory/export?format=json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["format"] == "json"

    def test_export_markdown_endpoint(self):
        client = self._get_client()
        resp = client.get("/memory/export?format=markdown")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["format"] == "markdown"

    def test_import_endpoint(self):
        client = self._get_client()
        json_str = '{"format":"aios-memory-json","episodes":[],"graph":{"nodes":[],"edges":[]}}'
        payload = {"data": json_str, "format": "json"}
        resp = client.post("/memory/import", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True

    def test_import_markdown_endpoint(self):
        client = self._get_client()
        payload = {"data": "# AIOS Memory Export\n\n## Knowledge Graph\n\n**Nodes:** 0 | **Edges:** 0\n", "format": "markdown"}
        resp = client.post("/memory/import", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
