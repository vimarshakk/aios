# M2.1 — Multi-Agent Execution

## Goal
Enable multiple agents to collaborate on complex tasks. A single user query triggers decomposition into subtasks, parallel execution across specialized agents, and result aggregation. This validates every M1 subsystem end-to-end.

## Why M2.1 First
- Tests the full stack: engine → context → memory → workflow → permissions → events
- Network effects: each new agent multiplies capability
- Validates the orchestrator as the central nervous system

---

## Architecture

```
User Query
    │
    ▼
Orchestrator.route(query, mode="multi")
    │
    ├─ TaskDecomposer.decompose(query, agent_capabilities)
    │    → Subtask[]
    │
    ├─ AgentPool.select(subtask, required_capabilities)
    │    → BaseAgent
    │
    ├─ MultiAgentExecutor.execute(subtasks, agents)
    │    ├─ subtask_1 → agent_A ─┐
    │    ├─ subtask_2 → agent_B ─┤  concurrent
    │    └─ subtask_3 → agent_C ─┘
    │    → SubtaskResult[]
    │
    └─ ResultAggregator.aggregate(subtask_results, query)
         → FinalResponse
```

---

## New Modules

### 1. `packages/agents/src/aios/agents/task.py` — Task Decomposition

```python
@dataclass(frozen=True)
class Subtask:
    id: str
    query: str
    required_capabilities: frozenset[str]
    dependencies: frozenset[str]   # subtask IDs this depends on
    priority: int                  # 0 = highest
    metadata: dict[str, Any]

class TaskDecomposer:
    def decompose(self, query: str, available_capabilities: set[str]) -> list[Subtask]
    # LLM-free heuristic decomposition: single task = [Subtask(query, all_caps)]
    # LLM-powered: future phase, for now simple rule-based
```

### 2. `packages/agents/src/aios/agents/pool.py` — Agent Pool

```python
@dataclass
class AgentEntry:
    name: str
    agent: BaseAgent
    capabilities: set[str]
    priority: int       # lower = preferred
    healthy: bool

class AgentPool:
    def register(self, name, agent, capabilities, priority=0) -> None
    def deregister(self, name) -> None
    def select(self, required_capabilities: set[str]) -> AgentEntry | None
    def list_healthy(self) -> list[AgentEntry]
    def mark_unhealthy(self, name) -> None
```

### 3. `packages/agents/src/aios/agents/multi_executor.py` — Parallel Execution

```python
@dataclass
class SubtaskResult:
    subtask_id: str
    agent_name: str
    response: str
    success: bool
    error: str | None
    duration_ms: float

class MultiAgentExecutor:
    async def execute(self, subtasks: list[Subtask], pool: AgentPool) -> list[SubtaskResult]
    # Executes independent subtasks concurrently via asyncio.gather
    # Respects dependency ordering (topological)
```

### 4. `packages/agents/src/aios/agents/aggregator.py` — Result Aggregation

```python
class ResultAggregator:
    def aggregate(self, results: list[SubtaskResult], query: str) -> str
    # M1: sequential concatenation with headers
    # Future: LLM-powered synthesis
```

### 5. Extend `Orchestrator` — Multi-Agent Mode

```python
class Orchestrator:
    async def route(self, query, *, mode="single", ...) -> str:
        if mode == "multi":
            return await self._route_multi(query, ...)
        return await self._route_single(query, ...)
    
    async def _route_multi(self, query, ...) -> str:
        # decompose → select → execute → aggregate → return
```

---

## Dependencies (what M1 subsystems get exercised)

| M1 Subsystem | How M2.1 Uses It |
|---|---|
| InferenceEngine | Each agent calls engine.complete() |
| BaseAgent | Agents run via agent.run() |
| EventBus | Decomposition, execution, aggregation events |
| ContextBuilder | Each agent builds context before responding |
| HybridMemoryManager | Shared memory across agents |
| CapabilityRegistry | Agent selection by capability |
| PermissionChecker | Each agent's permissions enforced |
| WorkflowExecutor | Subtask dependency ordering |
| PluginRuntime | Plugins can register as agents |

---

## Test Plan

| Test File | Tests | Covers |
|---|---|---|
| `test_task_decomposer.py` | 10 | Subtask creation, capability matching, dependency resolution |
| `test_agent_pool.py` | 12 | Register/deregister, select by capability, health checks |
| `test_multi_executor.py` | 10 | Parallel execution, dependency ordering, failure isolation |
| `test_aggregator.py` | 8 | Sequential, priority-sorted, failure handling |
| `test_orchestrator_multi.py` | 8 | End-to-end multi-agent routing |

**Target: 50+ new tests, 503+ total**

---

## Implementation Order

1. `task.py` — Subtask dataclass + TaskDecomposer
2. `pool.py` — AgentPool with capability matching
3. `multi_executor.py` — Parallel execution with dependency resolution
4. `aggregator.py` — Result aggregation
5. Extend `orchestrator/main.py` — multi-agent routing mode
6. `tests/test_m2_1.py` — All tests
7. Update `__init__.py` exports
8. Full suite + lint + contract verification

---

## Non-Goals (M2.2+)
- LLM-powered decomposition (rule-based for now)
- Dynamic agent creation at runtime
- Agent-to-agent messaging (use shared memory instead)
- Streaming multi-agent responses
- Agent specialization learning
