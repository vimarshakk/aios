"""KnowledgeGraph — in-memory graph structure for entity-relation-entity triples."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aios.memory.fact_store import Fact


@dataclass(frozen=True)
class GraphNode:
    """A node in the knowledge graph."""

    id: str
    label: str
    node_type: str  # "entity", "concept", "event", "fact"
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    """A directed edge (relation) between two nodes."""

    id: str
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """In-memory knowledge graph with traversal, pathfinding, and community detection.

    Stores entity-relation-entity triples as directed edges between typed nodes.
    Supports BFS/DFS traversal, shortest path (unweighted), cycle detection,
    and connected-component community detection.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}
        # Adjacency: source_id → list of edge ids
        self._adjacency: dict[str, list[str]] = {}
        # Reverse adjacency: target_id → list of edge ids
        self._reverse: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph. Overwrites if id exists."""
        self._nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> bool:
        """Add a directed edge. Returns False if source or target missing."""
        if edge.source_id not in self._nodes or edge.target_id not in self._nodes:
            return False
        self._edges[edge.id] = edge
        self._adjacency.setdefault(edge.source_id, []).append(edge.id)
        self._reverse.setdefault(edge.target_id, []).append(edge.id)
        return True

    def get_node(self, node_id: str) -> GraphNode | None:
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> GraphEdge | None:
        return self._edges.get(edge_id)

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its incident edges."""
        if node_id not in self._nodes:
            return False

        # Collect incident edge ids
        out_edges = list(self._adjacency.get(node_id, []))
        in_edges = list(self._reverse.get(node_id, []))
        for eid in out_edges + in_edges:
            self._remove_edge_by_id(eid)

        del self._nodes[node_id]
        self._adjacency.pop(node_id, None)
        self._reverse.pop(node_id, None)
        return True

    def remove_edge(self, edge_id: str) -> bool:
        return self._remove_edge_by_id(edge_id)

    def _remove_edge_by_id(self, edge_id: str) -> bool:
        edge = self._edges.pop(edge_id, None)
        if not edge:
            return False
        src_list = self._adjacency.get(edge.source_id, [])
        if edge_id in src_list:
            src_list.remove(edge_id)
        tgt_list = self._reverse.get(edge.target_id, [])
        if edge_id in tgt_list:
            tgt_list.remove(edge_id)
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_neighbors(self, node_id: str) -> list[tuple[GraphEdge, GraphNode]]:
        """Return outgoing neighbors (edge, node) pairs."""
        result: list[tuple[GraphEdge, GraphNode]] = []
        for eid in self._adjacency.get(node_id, []):
            edge = self._edges.get(eid)
            if edge:
                target = self._nodes.get(edge.target_id)
                if target:
                    result.append((edge, target))
        return result

    def get_edges_between(self, source: str, target: str) -> list[GraphEdge]:
        """Return all edges from source to target."""
        result: list[GraphEdge] = []
        for eid in self._adjacency.get(source, []):
            edge = self._edges.get(eid)
            if edge and edge.target_id == target:
                result.append(edge)
        return result

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def bfs(self, start_id: str, max_depth: int = -1) -> list[GraphNode]:
        """Breadth-first traversal from start_id. Returns nodes in visit order."""
        if start_id not in self._nodes:
            return []

        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])
        result: list[GraphNode] = []

        while queue:
            node_id, depth = queue.popleft()
            if node_id in visited:
                continue
            if max_depth >= 0 and depth > max_depth:
                continue

            visited.add(node_id)
            node = self._nodes.get(node_id)
            if node:
                result.append(node)

            for eid in self._adjacency.get(node_id, []):
                edge = self._edges.get(eid)
                if edge and edge.target_id not in visited:
                    queue.append((edge.target_id, depth + 1))

        return result

    def dfs(self, start_id: str, max_depth: int = -1) -> list[GraphNode]:
        """Depth-first traversal from start_id. Returns nodes in visit order."""
        if start_id not in self._nodes:
            return []

        visited: set[str] = set()
        stack: list[tuple[str, int]] = [(start_id, 0)]
        result: list[GraphNode] = []

        while stack:
            node_id, depth = stack.pop()
            if node_id in visited:
                continue
            if max_depth >= 0 and depth > max_depth:
                continue

            visited.add(node_id)
            node = self._nodes.get(node_id)
            if node:
                result.append(node)

            # Push in reverse order so first neighbor is processed first
            for eid in reversed(self._adjacency.get(node_id, [])):
                edge = self._edges.get(eid)
                if edge and edge.target_id not in visited:
                    stack.append((edge.target_id, depth + 1))

        return result

    def shortest_path(self, start_id: str, end_id: str) -> list[GraphNode] | None:
        """BFS shortest path (unweighted). Returns None if no path exists."""
        if start_id not in self._nodes or end_id not in self._nodes:
            return None

        if start_id == end_id:
            return [self._nodes[start_id]]

        visited: set[str] = {start_id}
        queue: deque[tuple[str, list[str]]] = deque([(start_id, [start_id])])

        while queue:
            current, path = queue.popleft()
            for eid in self._adjacency.get(current, []):
                edge = self._edges.get(eid)
                if not edge:
                    continue
                next_id = edge.target_id
                if next_id == end_id:
                    full_path = [*path, next_id]
                    return [self._nodes[nid] for nid in full_path]
                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, [*path, next_id]))

        return None

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def has_cycle(self) -> bool:
        """Detect if the directed graph contains a cycle (DFS-based)."""
        white, gray, black = 0, 1, 2
        color: dict[str, int] = dict.fromkeys(self._nodes, white)

        def dfs_visit(nid: str) -> bool:
            color[nid] = gray
            for eid in self._adjacency.get(nid, []):
                edge = self._edges.get(eid)
                if not edge:
                    continue
                neighbor = edge.target_id
                if color.get(neighbor) == gray:
                    return True
                if color.get(neighbor) == white and dfs_visit(neighbor):
                    return True
            color[nid] = black
            return False

        return any(
            color[nid] == white and dfs_visit(nid) for nid in self._nodes
        )

    def detect_communities(self) -> list[list[str]]:
        """Find connected components (undirected) as communities."""
        visited: set[str] = set()
        communities: list[list[str]] = []

        def _build_undirected() -> dict[str, set[str]]:
            undirected: dict[str, set[str]] = {nid: set() for nid in self._nodes}
            for edge in self._edges.values():
                undirected.setdefault(edge.source_id, set()).add(edge.target_id)
                undirected.setdefault(edge.target_id, set()).add(edge.source_id)
            return undirected

        adj = _build_undirected()

        for nid in self._nodes:
            if nid in visited:
                continue
            component: list[str] = []
            stack = [nid]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)
                stack.extend(
                    neighbor for neighbor in adj.get(current, set())
                    if neighbor not in visited
                )
            communities.append(sorted(component))

        return communities

    # ------------------------------------------------------------------
    # Bulk import
    # ------------------------------------------------------------------

    def from_facts(self, facts: list[Fact]) -> None:
        """Import facts as entity-relation-entity triples.

        Each Fact becomes: subject_node -[predicate]-> object_node.
        Nodes are created automatically if they don't exist.
        """
        for fact in facts:
            # Create or get subject node
            subj_id = f"entity:{fact.subject.lower()}"
            if subj_id not in self._nodes:
                self.add_node(GraphNode(
                    id=subj_id,
                    label=fact.subject,
                    node_type="entity",
                    properties={"source": fact.source} if fact.source else {},
                ))

            # Create or get object node
            obj_id = f"entity:{fact.obj.lower()}"
            if obj_id not in self._nodes:
                self.add_node(GraphNode(
                    id=obj_id,
                    label=fact.obj,
                    node_type="entity",
                ))

            # Create edge (predicate)
            edge_id = f"fact:{fact.id}"
            self.add_edge(GraphEdge(
                id=edge_id,
                source_id=subj_id,
                target_id=obj_id,
                relation=fact.predicate,
                weight=fact.confidence,
                properties={"source": fact.source} if fact.source else {},
            ))

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)


__all__ = [
    "GraphEdge",
    "GraphNode",
    "KnowledgeGraph",
]
