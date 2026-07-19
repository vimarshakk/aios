"""GraphQuery — pattern matching, neighborhood, and path queries over KnowledgeGraph."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from aios.memory.graph import GraphEdge, GraphNode, KnowledgeGraph


@dataclass
class PatternMatch:
    """A subgraph pattern match."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    score: float = 1.0


class GraphQuery:
    """Query interface for the knowledge graph.

    Supports type-based lookups, relation queries, multi-path finding,
    neighborhood expansion, pattern matching, and subgraph extraction.
    """

    def __init__(self, graph: KnowledgeGraph) -> None:
        self._graph = graph

    def find_by_type(self, node_type: str) -> list[GraphNode]:
        """Return all nodes of a given type."""
        return [
            node
            for node in self._graph._nodes.values()
            if node.node_type == node_type
        ]

    def find_by_relation(
        self, relation: str
    ) -> list[tuple[GraphNode, GraphEdge, GraphNode]]:
        """Return all (source, edge, target) triples for a given relation."""
        results: list[tuple[GraphNode, GraphEdge, GraphNode]] = []
        for edge in self._graph._edges.values():
            if edge.relation == relation:
                src = self._graph.get_node(edge.source_id)
                tgt = self._graph.get_node(edge.target_id)
                if src and tgt:
                    results.append((src, edge, tgt))
        return results

    def find_paths(
        self, start: str, end: str, max_depth: int = 5
    ) -> list[list[GraphNode]]:
        """Find all simple paths from start to end up to max_depth."""
        if start not in self._graph._nodes or end not in self._graph._nodes:
            return []

        paths: list[list[GraphNode]] = []
        queue: deque[tuple[str, list[str]]] = deque([(start, [start])])

        while queue:
            current, path = queue.popleft()
            if current == end:
                paths.append(
                    [self._graph._nodes[nid] for nid in path]
                )
                continue
            if len(path) > max_depth:
                continue

            for eid in self._graph._adjacency.get(current, []):
                edge = self._graph._edges.get(eid)
                if not edge:
                    continue
                next_id = edge.target_id
                if next_id not in path:  # Simple path: no revisiting
                    queue.append((next_id, [*path, next_id]))

        return paths

    def neighborhood(self, node_id: str, depth: int = 1) -> dict[str, Any]:
        """Return the neighborhood around a node as a dict of nodes and edges.

        Returns {"nodes": [...], "edges": [...]} expanding `depth` hops.
        """
        if node_id not in self._graph._nodes:
            return {"nodes": [], "edges": []}

        visited: set[str] = set()
        result_nodes: list[GraphNode] = []
        result_edges: list[GraphEdge] = []
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])

        while queue:
            current, d = queue.popleft()
            if current in visited or d > depth:
                continue
            visited.add(current)
            node = self._graph.get_node(current)
            if node:
                result_nodes.append(node)
            if d < depth:
                for eid in self._graph._adjacency.get(current, []):
                    edge = self._graph._edges.get(eid)
                    if edge and edge.target_id not in visited:
                        result_edges.append(edge)
                        queue.append((edge.target_id, d + 1))

        return {"nodes": result_nodes, "edges": result_edges}

    def find_pattern(self, pattern: dict[str, Any]) -> list[PatternMatch]:
        """Find subgraphs matching a pattern.

        Pattern keys:
          - "node_type": filter nodes by type
          - "relation": filter edges by relation
          - "min_weight": minimum edge weight

        Returns matching (source, edge, target) subgraphs.
        """
        node_type = pattern.get("node_type")
        relation = pattern.get("relation")
        min_weight = pattern.get("min_weight", 0.0)

        matches: list[PatternMatch] = []

        for edge in self._graph._edges.values():
            if relation and edge.relation != relation:
                continue
            if edge.weight < min_weight:
                continue

            src = self._graph.get_node(edge.source_id)
            tgt = self._graph.get_node(edge.target_id)
            if not src or not tgt:
                continue

            if node_type and src.node_type != node_type and tgt.node_type != node_type:
                continue

            matches.append(PatternMatch(
                nodes=[src, tgt],
                edges=[edge],
                score=edge.weight,
            ))

        return matches

    def subgraph(self, node_ids: set[str]) -> KnowledgeGraph:
        """Extract a subgraph containing only the specified nodes and their internal edges."""
        sub = KnowledgeGraph()
        for nid in node_ids:
            node = self._graph.get_node(nid)
            if node:
                sub.add_node(node)

        for edge in self._graph._edges.values():
            if edge.source_id in node_ids and edge.target_id in node_ids:
                sub.add_edge(edge)

        return sub


__all__ = [
    "GraphQuery",
    "PatternMatch",
]
