"""WorkspaceMemory — workspace-scoped memory isolation.

Each workspace maintains its own:
- Episodic memories
- Entity memory
- Knowledge Graph
- Vector index
- Facts

Supports multi-tenant memory where different projects/domains have isolated
memory spaces with independent consolidation and retrieval.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from aios.memory.entity import EntityMemory
from aios.memory.episodic import EpisodicMemory
from aios.memory.fact_store import Fact, JSONLFactStore
from aios.memory.graph import KnowledgeGraph
from aios.memory.vector_light import LightweightVectorMemory


@dataclass
class Workspace:
    """A memory workspace."""

    id: str
    name: str
    description: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    # Stats
    episode_count: int = 0
    entity_count: int = 0
    fact_count: int = 0
    graph_node_count: int = 0
    graph_edge_count: int = 0
    vector_doc_count: int = 0


@dataclass
class WorkspaceStats:
    """Statistics for a workspace."""

    episodes: int = 0
    entities: int = 0
    facts: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0
    vector_docs: int = 0


class WorkspaceMemory:
    """Manages workspace-scoped memory stores.

    Each workspace gets isolated:
    - EpisodicMemory (conversation history)
    - EntityMemory (people, places, things)
    - KnowledgeGraph (relationships)
    - LightweightVectorMemory (semantic search)
    - JSONLFactStore (extracted facts)

    Usage:
        wm = WorkspaceMemory()
        ws = wm.create_workspace("my-project", "My Project Description")
        await ws.episodic.store("Discussed architecture")
        results = await ws.vector.search("architecture")
    """

    def __init__(self) -> None:
        self._workspaces: dict[str, Workspace] = {}
        self._stores: dict[str, _WorkspaceStores] = {}

    def create_workspace(
        self,
        name: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Workspace:
        """Create a new workspace."""
        ws_id = f"ws_{uuid.uuid4().hex[:12]}"
        now = time.time()
        workspace = Workspace(
            id=ws_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        self._workspaces[ws_id] = workspace
        self._stores[ws_id] = _WorkspaceStores()
        return workspace

    def get_workspace(self, ws_id: str) -> Workspace | None:
        """Get a workspace by ID."""
        return self._workspaces.get(ws_id)

    def list_workspaces(self) -> list[Workspace]:
        """List all workspaces."""
        return list(self._workspaces.values())

    def delete_workspace(self, ws_id: str) -> bool:
        """Delete a workspace and all its data."""
        if ws_id in self._workspaces:
            del self._workspaces[ws_id]
            self._stores.pop(ws_id, None)
            return True
        return False

    def get_stores(self, ws_id: str) -> _WorkspaceStores | None:
        """Get the memory stores for a workspace."""
        return self._stores.get(ws_id)

    def get_or_create_workspace(
        self,
        name: str,
        description: str = "",
    ) -> Workspace:
        """Get existing workspace by name or create new one."""
        for ws in self._workspaces.values():
            if ws.name == name:
                return ws
        return self.create_workspace(name, description)

    def update_stats(self, ws_id: str) -> WorkspaceStats:
        """Update and return workspace stats."""
        workspace = self._workspaces.get(ws_id)
        stores = self._stores.get(ws_id)
        if not workspace or not stores:
            return WorkspaceStats()

        stats = WorkspaceStats(
            episodes=stores.episodic._max_entries,  # approximate
            entities=stores.entity._entities.__len__(),
            facts=stores.facts._facts.__len__(),
            graph_nodes=stores.graph.node_count(),
            graph_edges=stores.graph.edge_count(),
            vector_docs=stores.vector.count,
        )
        workspace.episode_count = stats.episodes
        workspace.entity_count = stats.entities
        workspace.fact_count = stats.facts
        workspace.graph_node_count = stats.graph_nodes
        workspace.graph_edge_count = stats.graph_edges
        workspace.vector_doc_count = stats.vector_docs
        workspace.updated_at = time.time()
        return stats


class _WorkspaceStores:
    """Internal container for a workspace's memory stores."""

    def __init__(self) -> None:
        self.episodic = EpisodicMemory()
        self.entity = EntityMemory()
        self.graph = KnowledgeGraph()
        self.vector = LightweightVectorMemory()
        self.facts = JSONLFactStore()  # in-memory JSONL (no file)


__all__ = [
    "Workspace",
    "WorkspaceMemory",
    "WorkspaceStats",
]
