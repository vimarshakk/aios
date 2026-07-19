# M2.2 — Memory Consolidation & Knowledge Graph

## Goal
Transform episodic memories into a persistent knowledge graph with entity-relation-entity triples, graph traversal, and automatic consolidation. Enable the system to "remember what it learned" across sessions.

## Why M2.2 After M2.1
- M2.1 validated the full stack end-to-end
- Multi-agent execution generates rich episodic memories that need consolidation
- Knowledge graph enables cross-session intelligence (not just per-session context)
- Foundation for M2.4 (self-improvement) — the system learns from consolidated knowledge

---

## Architecture

```
EpisodicMemory (episodes)
    │
    ▼
MemoryConsolidator.consolidate()
    │
    ├─ extract_facts(episode) → Fact[]
    │    (rule-based: subject-predicate-object extraction)
    │
    ├─ deduplicate(facts) → Fact[]
    │    (merge duplicates, keep highest confidence)
    │
    └─ store_in_graph(facts, KnowledgeGraph)
         │
         ▼
    KnowledgeGraph
    ├─ GraphNode[] (entities)
    ├─ GraphEdge[] (relations)
    ├─ BFS/DFS traversal
    ├─ Shortest path (Dijkstra)
    ├─ Community detection (connected components)
    └─ GraphQuery (pattern matching, neighborhood)
```

---

## New Modules

### 1. `packages/memory/src/aios/memory/graph.py` — Knowledge Graph

```python
@dataclass(frozen=True)
class GraphNode:
    id: str
    label: str
    node_type: str          # "entity", "concept", "event", "fact"
    properties: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class GraphEdge:
    id: str
    source_id: str          # GraphNode.id
    target_id: str          # GraphNode.id
    relation: str           # "works_at", "causes", "part_of", etc.
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)

class KnowledgeGraph:
    def add_node(self, node: GraphNode) -> None
    def add_edge(self, edge: GraphEdge) -> bool  # False if source/target missing
    def get_node(self, node_id: str) -> GraphNode | None
    def get_edge(self, edge_id: str) -> GraphEdge | None
    def remove_node(self, node_id: str) -> bool   # Also removes incident edges
    def remove_edge(self, edge_id: str) -> bool
    def get_neighbors(self, node_id: str) -> list[tuple[GraphEdge, GraphNode]]
    def get_edges_between(self, source: str, target: str) -> list[GraphEdge]
    def bfs(self, start_id: str, max_depth: int = -1) -> list[GraphNode]
    def dfs(self, start_id: str, max_depth: int = -1) -> list[GraphNode]
    def shortest_path(self, start_id: str, end_id: str) -> list[GraphNode] | None
    def detect_communities(self) -> list[list[str]]  # Connected components
    def has_cycle(self) -> bool
    def node_count(self) -> int
    def edge_count(self) -> int
    def from_facts(self, facts: list[Fact]) -> None  # Bulk import from FactStore
```

### 2. `packages/memory/src/aios/memory/consolidator.py` — Memory Consolidation

```python
@dataclass
class ConsolidationResult:
    facts_extracted: int
    facts_stored: int
    facts_deduplicated: int
    nodes_added: int
    edges_added: int

class MemoryConsolidator:
    def __init__(self, graph: KnowledgeGraph, fact_store: FactStore)
    async def consolidate_episode(self, episode: Episode) -> ConsolidationResult
    async def consolidate_batch(self, episodes: list[Episode]) -> ConsolidationResult
    async def consolidate_all(self, episodic: EpisodicMemory) -> ConsolidationResult
    def _extract_facts(self, text: str) -> list[Fact]  # Rule-based extraction
    def _deduplicate(self, facts: list[Fact]) -> list[Fact]
    def _prune(self, min_confidence: float = 0.3) -> int  # Remove low-confidence facts
```

### 3. `packages/memory/src/aios/memory/graph_query.py` — Graph Query Interface

```python
@dataclass
class PatternMatch:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    score: float

class GraphQuery:
    def __init__(self, graph: KnowledgeGraph)
    def find_by_type(self, node_type: str) -> list[GraphNode]
    def find_by_relation(self, relation: str) -> list[tuple[GraphNode, GraphEdge, GraphNode]]
    def find_paths(self, start: str, end: str, max_depth: int = 5) -> list[list[GraphNode]]
    def neighborhood(self, node_id: str, depth: int = 1) -> dict[str, Any]
    def find_pattern(self, pattern: dict[str, Any]) -> list[PatternMatch]
    def subgraph(self, node_ids: set[str]) -> KnowledgeGraph  # Extract subgraph
```

---

## Integration with HybridMemoryManager

The consolidator integrates via an optional consolidation hook:

```python
class HybridMemoryManager:
    def __init__(self) -> None:
        ...
        self._consolidator: MemoryConsolidator | None = None

    def set_consolidator(self, consolidator: MemoryConsolidator) -> None:
        self._consolidator = consolidator

    async def store(self, content, *, backend=None, metadata=None):
        doc_id = await target.backend.store(content, metadata=metadata or {})
        # Auto-consolidate if consolidator is set
        if self._consolidator and metadata and metadata.get("consolidate"):
            await self._consolidator.consolidate_episode(...)
        ...
```

---

## Dependencies (what M1/M2.1 subsystems get exercised)

| Subsystem | How M2.2 Uses It |
|---|---|
| EntityMemory | Entity extraction from episodes |
| FactStore | Triple storage for knowledge graph |
| EpisodicMemory | Source of memories to consolidate |
| HybridMemoryManager | Consolidation hook integration |
| EventBus | Consolidation lifecycle events |
| KnowledgeGraph | Core graph structure |

---

## Test Plan

| Test File | Tests | Covers |
|---|---|---|
| `test_knowledge_graph.py` | 20 | Node/edge CRUD, BFS/DFS, shortest path, cycle detection, community detection |
| `test_consolidator.py` | 12 | Fact extraction, dedup, consolidation pipeline, pruning |
| `test_graph_query.py` | 10 | Pattern matching, neighborhood, path queries, subgraph extraction |

**Target: 40+ new tests, 605+ total**

---

## Implementation Order

1. `graph.py` — KnowledgeGraph core (nodes, edges, traversal, pathfinding)
2. `graph_query.py` — Query interface (patterns, neighborhood, subgraph)
3. `consolidator.py` — MemoryConsolidator (extraction, dedup, pruning)
4. Update `__init__.py` exports
5. `tests/test_m2_2.py` — All tests
6. Full suite + lint + contract verification

---

## Non-Goals (M2.3+)
- LLM-powered fact extraction (rule-based for now)
- Persistent graph serialization (in-memory for M2.2)
- Graph neural networks
- Temporal reasoning over facts
- Cross-graph merging
