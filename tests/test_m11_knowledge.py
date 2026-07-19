"""Tests for M11.1 — LightweightVectorMemory and M11.2 — Graph REST endpoints."""

import asyncio
import pytest
from aios.memory.vector_light import LightweightVectorMemory, SearchResult


# ---------------------------------------------------------------------------
# M11.1: LightweightVectorMemory
# ---------------------------------------------------------------------------

class TestLightweightVectorMemory:

    def test_add_and_search(self):
        mem = LightweightVectorMemory()
        mem.add("The quick brown fox jumps over the lazy dog", doc_id="a1")
        mem.add("Python is a popular programming language", doc_id="a2")
        mem.add("Machine learning is a subset of artificial intelligence", doc_id="a3")

        results = mem.search("programming language", top_k=2)
        assert len(results) <= 2
        assert any("Python" in r.content for r in results)

    def test_search_empty(self):
        mem = LightweightVectorMemory()
        results = mem.search("anything", top_k=5)
        assert results == []

    def test_remove(self):
        mem = LightweightVectorMemory()
        mem.add("Hello world", doc_id="a1")
        mem.add("Goodbye world", doc_id="a2")
        assert mem.count == 2
        removed = mem.remove("a1")
        assert removed is True
        assert mem.count == 1
        removed = mem.remove("nonexistent")
        assert removed is False

    def test_search_with_metadata(self):
        mem = LightweightVectorMemory()
        mem.add("The cat sat on the mat", metadata={"source": "book"}, doc_id="a1")
        mem.add("The dog ran in the park", metadata={"source": "web"}, doc_id="a2")

        results = mem.search("cat mat", top_k=5)
        assert len(results) >= 1
        assert results[0].metadata.get("source") == "book"

    def test_import_episodes(self):
        mem = LightweightVectorMemory()
        episodes = [
            {"id": "ep1", "content": "Alice met Bob at the coffee shop"},
            {"id": "ep2", "content": "Bob discussed quantum physics with Charlie"},
            {"id": "ep3", "content": "Charlie recommended a book to Alice"},
        ]
        imported = mem.import_episodes(episodes)
        assert imported == 3
        assert mem.count == 3

    def test_import_episodes_missing_fields(self):
        mem = LightweightVectorMemory()
        episodes = [
            {"id": "ep1"},  # no content — skipped
            {"content": "Some text without id"},  # no id — gets auto-generated, imported
            {"id": "ep3", "content": "Valid episode"},
        ]
        imported = mem.import_episodes(episodes)
        assert imported == 2

    def test_export(self):
        mem = LightweightVectorMemory()
        mem.add("First document", metadata={"tag": "test"}, doc_id="a1")
        mem.add("Second document", doc_id="a2")
        exported = mem.export_all()
        assert len(exported) == 2
        assert exported[0]["id"] == "a1"
        assert exported[0]["content"] == "First document"

    def test_top_k_limits_results(self):
        mem = LightweightVectorMemory()
        for i in range(20):
            mem.add(f"Document number {i} about testing", doc_id=f"d{i}")
        results = mem.search("testing document", top_k=5)
        assert len(results) == 5

    def test_search_scores_ordered_desc(self):
        mem = LightweightVectorMemory()
        mem.add("Python programming language", doc_id="a1")
        mem.add("Java programming language", doc_id="a2")
        mem.add("The weather is nice today", doc_id="a3")
        results = mem.search("Python programming", top_k=3)
        if len(results) >= 2:
            assert results[0].score >= results[1].score

    def test_count(self):
        mem = LightweightVectorMemory()
        assert mem.count == 0
        mem.add("Hello", doc_id="a1")
        assert mem.count == 1
        mem.add("World", doc_id="a2")
        assert mem.count == 2
        mem.remove("a1")
        assert mem.count == 1


# ---------------------------------------------------------------------------
# M11.2: KnowledgeGraph REST API (unit test the graph methods we added)
# ---------------------------------------------------------------------------

class TestKnowledgeGraphExtended:
    """Test the new methods added to KnowledgeGraph for M11.2."""

    def test_list_nodes(self):
        from aios.memory.graph import GraphNode, KnowledgeGraph

        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="Alice", node_type="person"))
        g.add_node(GraphNode(id="n2", label="Bob", node_type="person"))
        nodes = g.list_nodes()
        assert len(nodes) == 2
        labels = {n.label for n in nodes}
        assert labels == {"Alice", "Bob"}

    def test_list_edges(self):
        from aios.memory.graph import GraphEdge, GraphNode, KnowledgeGraph

        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="thing"))
        g.add_node(GraphNode(id="n2", label="B", node_type="thing"))
        g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="knows"))
        edges = g.list_edges()
        assert len(edges) == 1
        assert edges[0].relation == "knows"

    def test_get_outgoing_edges(self):
        from aios.memory.graph import GraphEdge, GraphNode, KnowledgeGraph

        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="thing"))
        g.add_node(GraphNode(id="n2", label="B", node_type="thing"))
        g.add_node(GraphNode(id="n3", label="C", node_type="thing"))
        g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="likes"))
        g.add_edge(GraphEdge(id="e2", source_id="n1", target_id="n3", relation="follows"))
        g.add_edge(GraphEdge(id="e3", source_id="n2", target_id="n3", relation="knows"))
        out = g.get_outgoing_edges("n1")
        assert len(out) == 2
        rels = {e.relation for e in out}
        assert rels == {"likes", "follows"}

    def test_get_incoming_edges(self):
        from aios.memory.graph import GraphEdge, GraphNode, KnowledgeGraph

        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="thing"))
        g.add_node(GraphNode(id="n2", label="B", node_type="thing"))
        g.add_node(GraphNode(id="n3", label="C", node_type="thing"))
        g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n3", relation="likes"))
        g.add_edge(GraphEdge(id="e2", source_id="n2", target_id="n3", relation="follows"))
        inc = g.get_incoming_edges("n3")
        assert len(inc) == 2

    def test_connected_components(self):
        from aios.memory.graph import GraphEdge, GraphNode, KnowledgeGraph

        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="thing"))
        g.add_node(GraphNode(id="n2", label="B", node_type="thing"))
        g.add_node(GraphNode(id="n3", label="C", node_type="thing"))
        g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="likes"))
        # n3 is isolated
        assert g.connected_components() == 2

    def test_remove_node_cleans_edges(self):
        from aios.memory.graph import GraphEdge, GraphNode, KnowledgeGraph

        g = KnowledgeGraph()
        g.add_node(GraphNode(id="n1", label="A", node_type="thing"))
        g.add_node(GraphNode(id="n2", label="B", node_type="thing"))
        g.add_edge(GraphEdge(id="e1", source_id="n1", target_id="n2", relation="likes"))
        g.remove_node("n1")
        assert g.get_node("n1") is None
        assert len(g.list_edges()) == 0
        assert g.get_incoming_edges("n2") == []
        assert g.get_outgoing_edges("n1") == []


# ---------------------------------------------------------------------------
# M11.2: KnowledgeGraph REST endpoints (HTTP test)
# ---------------------------------------------------------------------------

@pytest.fixture
def graph_client():
    """Create a FastAPI TestClient for the graph endpoints."""
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from pydantic import BaseModel
    from typing import Any
    import uuid

    from aios.memory.graph import GraphNode, GraphEdge, KnowledgeGraph

    # Build a minimal app with just the graph endpoints
    test_app = FastAPI()
    _graph = KnowledgeGraph()

    class GraphNodeRequest(BaseModel):
        label: str
        node_type: str = "entity"
        properties: dict[str, Any] = {}

    class GraphEdgeRequest(BaseModel):
        source_id: str
        target_id: str
        relation: str
        weight: float = 1.0
        properties: dict[str, Any] = {}

    @test_app.get("/graph/nodes")
    async def list_nodes(node_type: str | None = None, limit: int = 100):
        nodes = _graph.list_nodes()
        if node_type:
            nodes = [n for n in nodes if n.node_type == node_type]
        return [{"id": n.id, "label": n.label, "node_type": n.node_type, "properties": n.properties} for n in nodes[:limit]]

    @test_app.post("/graph/nodes")
    async def add_node(req: GraphNodeRequest):
        node_id = f"n_{uuid.uuid4().hex[:12]}"
        node = GraphNode(id=node_id, label=req.label, node_type=req.node_type, properties=req.properties)
        _graph.add_node(node)
        return {"id": node.id, "label": node.label, "node_type": node.node_type, "properties": node.properties}

    @test_app.delete("/graph/nodes/{node_id}")
    async def delete_node(node_id: str):
        removed = _graph.remove_node(node_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"message": f"Node {node_id} removed"}

    @test_app.post("/graph/edges")
    async def add_edge(req: GraphEdgeRequest):
        edge_id = f"e_{uuid.uuid4().hex[:12]}"
        edge = GraphEdge(id=edge_id, source_id=req.source_id, target_id=req.target_id, relation=req.relation, weight=req.weight, properties=req.properties)
        added = _graph.add_edge(edge)
        if not added:
            raise HTTPException(status_code=400, detail="Source or target node not found")
        return {"id": edge.id, "source_id": edge.source_id, "target_id": edge.target_id, "relation": edge.relation, "weight": edge.weight}

    @test_app.get("/graph/edges")
    async def list_edges(source_id: str | None = None, target_id: str | None = None, relation: str | None = None, limit: int = 100):
        edges = _graph.list_edges()
        if source_id:
            edges = [e for e in edges if e.source_id == source_id]
        if target_id:
            edges = [e for e in edges if e.target_id == target_id]
        if relation:
            edges = [e for e in edges if e.relation == relation]
        return [{"id": e.id, "source_id": e.source_id, "target_id": e.target_id, "relation": e.relation, "weight": e.weight, "properties": e.properties} for e in edges[:limit]]

    @test_app.get("/graph/stats")
    async def graph_stats():
        nodes = _graph.list_nodes()
        edges = _graph.list_edges()
        type_counts: dict[str, int] = {}
        for n in nodes:
            type_counts[n.node_type] = type_counts.get(n.node_type, 0) + 1
        return {"total_nodes": len(nodes), "total_edges": len(edges), "node_types": type_counts, "connected_components": _graph.connected_components()}

    @test_app.post("/graph/path")
    async def find_path(body: dict):
        path = _graph.shortest_path(body["source_id"], body["target_id"])
        if path is None:
            return {"found": False, "path": [], "length": 0}
        nodes = [{"id": n.id, "label": n.label} for n in path]
        return {"found": True, "path": nodes, "length": len(nodes)}

    client = TestClient(test_app)
    return client


class TestGraphEndpoints:

    def test_add_and_list_nodes(self, graph_client):
        resp = graph_client.post("/graph/nodes", json={"label": "Alice", "node_type": "person"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["label"] == "Alice"
        assert data["node_type"] == "person"
        node_id = data["id"]

        resp = graph_client.get("/graph/nodes")
        assert resp.status_code == 200
        nodes = resp.json()
        assert any(n["id"] == node_id for n in nodes)

    def test_filter_by_type(self, graph_client):
        graph_client.post("/graph/nodes", json={"label": "Alice", "node_type": "person"})
        graph_client.post("/graph/nodes", json={"label": "Python", "node_type": "language"})
        resp = graph_client.get("/graph/nodes", params={"node_type": "person"})
        assert len(resp.json()) == 1
        assert resp.json()[0]["label"] == "Alice"

    def test_delete_node(self, graph_client):
        resp = graph_client.post("/graph/nodes", json={"label": "Temp"})
        nid = resp.json()["id"]
        resp = graph_client.delete(f"/graph/nodes/{nid}")
        assert resp.status_code == 200
        resp = graph_client.get("/graph/nodes")
        assert not any(n["id"] == nid for n in resp.json())

    def test_delete_nonexistent_node(self, graph_client):
        resp = graph_client.delete("/graph/nodes/nonexistent")
        assert resp.status_code == 404

    def test_add_and_list_edges(self, graph_client):
        n1 = graph_client.post("/graph/nodes", json={"label": "A"}).json()["id"]
        n2 = graph_client.post("/graph/nodes", json={"label": "B"}).json()["id"]
        resp = graph_client.post("/graph/edges", json={"source_id": n1, "target_id": n2, "relation": "knows"})
        assert resp.status_code == 200
        assert resp.json()["relation"] == "knows"

        resp = graph_client.get("/graph/edges")
        assert len(resp.json()) == 1

    def test_add_edge_missing_node(self, graph_client):
        resp = graph_client.post("/graph/edges", json={"source_id": "bad", "target_id": "bad", "relation": "likes"})
        assert resp.status_code == 400

    def test_stats(self, graph_client):
        graph_client.post("/graph/nodes", json={"label": "A", "node_type": "person"})
        graph_client.post("/graph/nodes", json={"label": "B", "node_type": "language"})
        resp = graph_client.get("/graph/stats")
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["total_nodes"] == 2
        assert stats["node_types"]["person"] == 1

    def test_find_path(self, graph_client):
        n1 = graph_client.post("/graph/nodes", json={"label": "Start"}).json()["id"]
        n2 = graph_client.post("/graph/nodes", json={"label": "Mid"}).json()["id"]
        n3 = graph_client.post("/graph/nodes", json={"label": "End"}).json()["id"]
        graph_client.post("/graph/edges", json={"source_id": n1, "target_id": n2, "relation": "next"})
        graph_client.post("/graph/edges", json={"source_id": n2, "target_id": n3, "relation": "next"})

        resp = graph_client.post("/graph/path", json={"source_id": n1, "target_id": n3})
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["length"] == 3

    def test_find_path_no_route(self, graph_client):
        n1 = graph_client.post("/graph/nodes", json={"label": "A"}).json()["id"]
        n2 = graph_client.post("/graph/nodes", json={"label": "B"}).json()["id"]
        resp = graph_client.post("/graph/path", json={"source_id": n1, "target_id": n2})
        assert resp.json()["found"] is False
