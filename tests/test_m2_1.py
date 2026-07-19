"""M2.1 tests — Multi-agent execution: decomposer, pool, executor, aggregator, orchestrator."""

from __future__ import annotations

import asyncio

import pytest

from aios.agents.aggregator import ResultAggregator
from aios.agents.base import BaseAgent
from aios.agents.multi_executor import MultiAgentExecutor, SubtaskResult
from aios.agents.pool import AgentPool
from aios.agents.task import Subtask, TaskDecomposer, resolve_execution_order
from aios.orchestrator.main import Orchestrator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class StubAgent(BaseAgent):
    """Minimal agent that returns a canned response."""

    def __init__(self, response: str = "ok") -> None:
        self._response = response

    async def run(self, query: str) -> str:
        return self._response

    async def step(self, query: str) -> str:
        return self._response


class SlowAgent(BaseAgent):
    """Agent that takes a delay before responding."""

    def __init__(self, response: str = "slow", delay: float = 0.05) -> None:
        self._response = response
        self._delay = delay

    async def run(self, query: str) -> str:
        await asyncio.sleep(self._delay)
        return self._response

    async def step(self, query: str) -> str:
        return self._response


class FailAgent(BaseAgent):
    """Agent that raises on run."""

    async def run(self, query: str) -> str:
        raise RuntimeError("agent failure")

    async def step(self, query: str) -> str:
        raise RuntimeError("agent failure")


@pytest.fixture
def pool() -> AgentPool:
    p = AgentPool()
    p.register("math", StubAgent("42"), {"arithmetic", "math"}, priority=0)
    p.register("code", StubAgent("def hello()"), {"python", "code"}, priority=1)
    p.register("general", StubAgent("general answer"), {"general"}, priority=2)
    return p


@pytest.fixture
def decomposer() -> TaskDecomposer:
    return TaskDecomposer()


@pytest.fixture
def aggregator() -> ResultAggregator:
    return ResultAggregator()


# ===========================================================================
# TaskDecomposer
# ===========================================================================


class TestSubtaskDataclass:
    def test_create_subtask(self) -> None:
        s = Subtask(query="test", required_capabilities=frozenset({"a"}))
        assert s.query == "test"
        assert s.priority == 0
        assert s.id  # auto-generated

    def test_depends_on(self) -> None:
        a = Subtask(id="a", query="a")
        b = Subtask(id="b", query="b", dependencies=frozenset({"a"}))
        assert b.depends_on(a)
        assert not a.depends_on(b)

    def test_is_ready(self) -> None:
        s = Subtask(id="b", query="b", dependencies=frozenset({"a"}))
        assert s.is_ready({"a"})
        assert not s.is_ready(set())

    def test_is_ready_no_deps(self) -> None:
        s = Subtask(id="root", query="root")
        assert s.is_ready(set())
        assert s.is_ready({"anything"})


class TestTaskDecomposer:
    def test_single_query(self, decomposer: TaskDecomposer) -> None:
        result = decomposer.decompose("hello", {"general"})
        assert len(result) == 1
        assert result[0].query == "hello"

    def test_empty_capabilities(self, decomposer: TaskDecomposer) -> None:
        result = decomposer.decompose("do something", set())
        assert len(result) == 1
        assert result[0].query == "do something"

    def test_split_and_then(self, decomposer: TaskDecomposer) -> None:
        result = decomposer.decompose("do A and then do B", {"general"})
        assert len(result) == 2
        assert "A" in result[0].query
        assert "B" in result[1].query

    def test_split_semicolon(self, decomposer: TaskDecomposer) -> None:
        result = decomposer.decompose("step 1; step 2; step 3", {"general"})
        assert len(result) == 3

    def test_split_pipe(self, decomposer: TaskDecomposer) -> None:
        result = decomposer.decompose("task A | task B", {"general"})
        assert len(result) == 2

    def test_split_newlines(self, decomposer: TaskDecomposer) -> None:
        result = decomposer.decompose("line one\nline two\nline three", {"general"})
        assert len(result) == 3

    def test_infer_capabilities(self, decomposer: TaskDecomposer) -> None:
        result = decomposer.decompose("do arithmetic", {"arithmetic", "code"})
        assert len(result) == 1
        assert "arithmetic" in result[0].required_capabilities

    def test_no_match_uses_all(self, decomposer: TaskDecomposer) -> None:
        result = decomposer.decompose("do X", {"arithmetic", "code"})
        assert len(result) == 1
        assert result[0].required_capabilities == frozenset({"arithmetic", "code"})

    def test_multi_part_infer(self, decomposer: TaskDecomposer) -> None:
        result = decomposer.decompose(
            "write python code and then do arithmetic",
            {"python", "arithmetic"},
        )
        assert len(result) == 2
        # First part should match python
        assert "python" in result[0].required_capabilities

    def test_priority_assigned(self, decomposer: TaskDecomposer) -> None:
        result = decomposer.decompose("A and then B and then C", {"general"})
        assert len(result) == 3
        assert result[0].priority == 0
        assert result[1].priority == 1
        assert result[2].priority == 2


class TestResolveExecutionOrder:
    def test_empty(self) -> None:
        assert resolve_execution_order([]) == []

    def test_no_deps(self) -> None:
        a = Subtask(id="a", query="a")
        b = Subtask(id="b", query="b")
        layers = resolve_execution_order([a, b])
        assert len(layers) == 1
        assert len(layers[0]) == 2

    def test_linear_deps(self) -> None:
        a = Subtask(id="a", query="a")
        b = Subtask(id="b", query="b", dependencies=frozenset({"a"}))
        c = Subtask(id="c", query="c", dependencies=frozenset({"b"}))
        layers = resolve_execution_order([a, b, c])
        assert len(layers) == 3
        assert layers[0][0].id == "a"
        assert layers[1][0].id == "b"
        assert layers[2][0].id == "c"

    def test_parallel_deps(self) -> None:
        a = Subtask(id="a", query="a")
        b = Subtask(id="b", query="b")
        c = Subtask(id="c", query="c", dependencies=frozenset({"a", "b"}))
        layers = resolve_execution_order([a, b, c])
        assert len(layers) == 2
        assert len(layers[0]) == 2  # a and b in parallel
        assert layers[1][0].id == "c"

    def test_circular_breaks(self) -> None:
        a = Subtask(id="a", query="a", dependencies=frozenset({"b"}))
        b = Subtask(id="b", query="b", dependencies=frozenset({"a"}))
        layers = resolve_execution_order([a, b])
        assert len(layers) >= 1  # should not infinite loop


# ===========================================================================
# AgentPool
# ===========================================================================


class TestAgentPool:
    def test_register(self, pool: AgentPool) -> None:
        assert "math" in pool
        assert len(pool) == 3

    def test_deregister(self, pool: AgentPool) -> None:
        assert pool.deregister("math")
        assert "math" not in pool
        assert not pool.deregister("nonexistent")

    def test_get(self, pool: AgentPool) -> None:
        entry = pool.get("math")
        assert entry is not None
        assert entry.name == "math"
        assert entry.healthy

    def test_select_exact_match(self, pool: AgentPool) -> None:
        entry = pool.select({"arithmetic"})
        assert entry is not None
        assert "arithmetic" in entry.capabilities

    def test_select_multiple_caps(self, pool: AgentPool) -> None:
        entry = pool.select({"arithmetic", "math"})
        assert entry is not None
        assert entry.name == "math"

    def test_select_no_match(self, pool: AgentPool) -> None:
        entry = pool.select({"nonexistent"})
        assert entry is None

    def test_select_respects_priority(self) -> None:
        p = AgentPool()
        p.register("slow", StubAgent("slow"), {"code"}, priority=2)
        p.register("fast", StubAgent("fast"), {"code"}, priority=0)
        entry = p.select({"code"})
        assert entry is not None
        assert entry.name == "fast"

    def test_select_skips_unhealthy(self) -> None:
        p = AgentPool()
        p.register("a", StubAgent("a"), {"code"})
        p.mark_unhealthy("a")
        assert p.select({"code"}) is None

    def test_list_healthy(self, pool: AgentPool) -> None:
        pool.mark_unhealthy("math")
        healthy = pool.list_healthy()
        assert len(healthy) == 2
        assert all(e.healthy for e in healthy)

    def test_capabilities_summary(self, pool: AgentPool) -> None:
        summary = pool.capabilities_summary()
        assert "math" in summary
        assert "arithmetic" in summary["math"]

    def test_all_capabilities(self, pool: AgentPool) -> None:
        caps = pool.all_capabilities()
        assert "arithmetic" in caps
        assert "python" in caps
        assert "general" in caps

    def test_select_all(self, pool: AgentPool) -> None:
        entries = pool.select_all({"general"})
        assert len(entries) == 1
        assert entries[0].name == "general"


# ===========================================================================
# MultiAgentExecutor
# ===========================================================================


class TestMultiAgentExecutor:
    @pytest.mark.asyncio
    async def test_execute_single(self, pool: AgentPool) -> None:
        executor = MultiAgentExecutor(pool)
        subtask = Subtask(query="hello", required_capabilities=frozenset({"general"}))
        results = await executor.execute([subtask])
        assert len(results) == 1
        assert results[0].success
        assert results[0].response == "general answer"

    @pytest.mark.asyncio
    async def test_execute_parallel(self) -> None:
        p = AgentPool()
        p.register("a", SlowAgent("fast-a", 0.01), {"a"}, priority=0)
        p.register("b", SlowAgent("fast-b", 0.01), {"b"}, priority=0)

        executor = MultiAgentExecutor(p)
        tasks = [
            Subtask(query="task A", required_capabilities=frozenset({"a"})),
            Subtask(query="task B", required_capabilities=frozenset({"b"})),
        ]
        results = await executor.execute(tasks)
        assert len(results) == 2
        assert all(r.success for r in results)
        responses = {r.response for r in results}
        assert "fast-a" in responses
        assert "fast-b" in responses

    @pytest.mark.asyncio
    async def test_execute_no_agent(self) -> None:
        p = AgentPool()
        executor = MultiAgentExecutor(p)
        subtask = Subtask(query="hello", required_capabilities=frozenset({"missing"}))
        results = await executor.execute([subtask])
        assert len(results) == 1
        assert not results[0].success
        assert "No agent" in results[0].error

    @pytest.mark.asyncio
    async def test_execute_failure_isolation(self) -> None:
        p = AgentPool()
        p.register("good", StubAgent("ok"), {"good"}, priority=0)
        p.register("bad", FailAgent(), {"bad"}, priority=0)

        executor = MultiAgentExecutor(p)
        tasks = [
            Subtask(query="good task", required_capabilities=frozenset({"good"})),
            Subtask(query="bad task", required_capabilities=frozenset({"bad"})),
        ]
        results = await executor.execute(tasks)
        assert len(results) == 2
        good = next(r for r in results if r.agent_name == "good")
        bad = next(r for r in results if r.agent_name == "bad")
        assert good.success
        assert not bad.success
        assert "agent failure" in bad.error

    @pytest.mark.asyncio
    async def test_execute_records_duration(self, pool: AgentPool) -> None:
        executor = MultiAgentExecutor(pool)
        subtask = Subtask(query="hello", required_capabilities=frozenset({"general"}))
        results = await executor.execute([subtask])
        assert results[0].duration_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_respects_dependencies(self) -> None:
        p = AgentPool()
        p.register("a", StubAgent("result-a"), {"a"}, priority=0)
        p.register("b", StubAgent("result-b"), {"b"}, priority=0)

        executor = MultiAgentExecutor(p)
        a = Subtask(id="a", query="task A", required_capabilities=frozenset({"a"}))
        b = Subtask(
            id="b", query="task B",
            required_capabilities=frozenset({"b"}),
            dependencies=frozenset({"a"}),
        )
        results = await executor.execute([a, b])
        assert len(results) == 2
        assert results[0].subtask_id == "a"
        assert results[1].subtask_id == "b"

    @pytest.mark.asyncio
    async def test_execute_empty(self, pool: AgentPool) -> None:
        executor = MultiAgentExecutor(pool)
        results = await executor.execute([])
        assert results == []

    @pytest.mark.asyncio
    async def test_get_result(self, pool: AgentPool) -> None:
        executor = MultiAgentExecutor(pool)
        subtask = Subtask(query="hello", required_capabilities=frozenset({"general"}))
        await executor.execute([subtask])
        result = executor.get_result(subtask.id)
        assert result is not None
        assert result.success

    @pytest.mark.asyncio
    async def test_clear(self, pool: AgentPool) -> None:
        executor = MultiAgentExecutor(pool)
        subtask = Subtask(query="hello", required_capabilities=frozenset({"general"}))
        await executor.execute([subtask])
        executor.clear()
        assert executor.get_result(subtask.id) is None


# ===========================================================================
# ResultAggregator
# ===========================================================================


class TestResultAggregator:
    def test_empty(self, aggregator: ResultAggregator) -> None:
        result = aggregator.aggregate([], "test")
        assert "No results" in result

    def test_single_success(self, aggregator: ResultAggregator) -> None:
        results = [SubtaskResult("1", "agent", "hello world", True)]
        result = aggregator.aggregate(results, "test")
        assert result == "hello world"

    def test_single_failure(self, aggregator: ResultAggregator) -> None:
        results = [SubtaskResult("1", "agent", "", False, error="boom")]
        result = aggregator.aggregate(results, "test")
        assert "boom" in result
        assert "failed" in result

    def test_multiple_success(self, aggregator: ResultAggregator) -> None:
        results = [
            SubtaskResult("1", "agent-a", "result A", True),
            SubtaskResult("2", "agent-b", "result B", True),
        ]
        result = aggregator.aggregate(results, "test")
        assert "result A" in result
        assert "result B" in result
        assert "agent-a" in result
        assert "agent-b" in result

    def test_mixed_success_failure(self, aggregator: ResultAggregator) -> None:
        results = [
            SubtaskResult("1", "agent-a", "ok", True),
            SubtaskResult("2", "agent-b", "", False, error="fail"),
        ]
        result = aggregator.aggregate(results, "test")
        assert "ok" in result
        assert "fail" in result

    def test_aggregate_structured(self, aggregator: ResultAggregator) -> None:
        results = [
            SubtaskResult("1", "a", "r1", True, duration_ms=10.0),
            SubtaskResult("2", "b", "", False, error="e", duration_ms=5.0),
        ]
        structured = aggregator.aggregate_structured(results, "test")
        assert structured["total_subtasks"] == 2
        assert structured["succeeded"] == 1
        assert structured["failed"] == 1
        assert len(structured["results"]) == 1
        assert len(structured["errors"]) == 1
        assert structured["total_duration_ms"] == 15.0

    def test_aggregate_preserves_order(self, aggregator: ResultAggregator) -> None:
        results = [
            SubtaskResult("3", "c", "third", True),
            SubtaskResult("1", "a", "first", True),
            SubtaskResult("2", "b", "second", True),
        ]
        structured = aggregator.aggregate_structured(results, "test")
        ids = [r["subtask_id"] for r in structured["results"]]
        assert ids == ["3", "1", "2"]


# ===========================================================================
# Orchestrator multi-agent mode
# ===========================================================================


class TestOrchestratorMultiAgent:
    @pytest.mark.asyncio
    async def test_single_mode_unchanged(self) -> None:
        orch = Orchestrator()
        orch.register_agent("default", StubAgent("hello"))
        result = await orch.route("hi", mode="single")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_multi_mode_no_pool(self) -> None:
        orch = Orchestrator()
        result = await orch.route("do something complex", mode="multi")
        assert "No results" in result or "No agent" in result

    @pytest.mark.asyncio
    async def test_multi_mode_with_pool(self) -> None:
        orch = Orchestrator()
        orch.register_agent("math", StubAgent("42"), {"arithmetic"})
        orch.register_agent("code", StubAgent("code here"), {"python"})
        result = await orch.route("write python code", mode="multi")
        assert result  # non-empty

    @pytest.mark.asyncio
    async def test_multi_mode_creates_session(self) -> None:
        orch = Orchestrator()
        orch.register_agent("general", StubAgent("ok"), {"general"})
        result = await orch.route("hello", mode="multi")
        sessions = orch.list_sessions()
        assert len(sessions) == 1
        assert result

    @pytest.mark.asyncio
    async def test_multi_mode_reuses_session(self) -> None:
        orch = Orchestrator()
        orch.register_agent("general", StubAgent("ok"), {"general"})
        orch.get_or_create_session("test123")
        await orch.route("hello", session_id="test123", mode="multi")
        assert len(orch.list_sessions()) == 1

    @pytest.mark.asyncio
    async def test_multi_mode_failure_isolation(self) -> None:
        orch = Orchestrator()
        orch.register_agent("good", StubAgent("success"), {"good"})
        orch.register_agent("bad", FailAgent(), {"bad"})
        result = await orch.route("do good and bad", mode="multi")
        assert result  # should still return something

    @pytest.mark.asyncio
    async def test_pool_property(self) -> None:
        orch = Orchestrator()
        assert isinstance(orch.pool, AgentPool)

    @pytest.mark.asyncio
    async def test_register_agent_with_caps(self) -> None:
        orch = Orchestrator()
        orch.register_agent("test", StubAgent(), {"cap1"}, priority=5)
        assert "test" in orch.pool
        entry = orch.pool.get("test")
        assert entry is not None
        assert entry.priority == 5
