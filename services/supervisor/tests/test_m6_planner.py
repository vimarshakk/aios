"""Tests for the M6 autonomous planner + native executor pipeline (ADR-0024).

Follows the existing ``_FakePlatform`` pattern from test_supervisor.py: a duck-
typed platform that records skill executions and resolves every capability to a
native skill, so the planner→graph→executor→resolver flow is exercised end to
end without launching a browser or desktop notification.
"""

from __future__ import annotations

import asyncio

from aios.skills.base import SkillResult, SkillStatus
from aios.supervisor import (
    AutonomousPlanner,
    NativeGoalRunner,
    Supervisor,
    Task,
    TaskGraph,
    validate_task_graph,
)
from aios.supervisor.planner import _parse_llm_tasks


class _FakeSkill:
    def __init__(self, name: str, caps: tuple[str, ...]) -> None:
        self._name = name
        self._caps = caps

    @property
    def manifest(self):
        class _M:
            capabilities = self._caps

        return _M()

    async def run(self, ctx):
        from aios.skills.base import SkillResult, SkillStatus

        return SkillResult(
            status=SkillStatus.SUCCESS,
            outputs={"ran": self._name, "action": ctx.inputs.get("action")},
        )


class _FakePlatform:
    """Records execute_skill calls; resolves any capability to a native skill."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._skills = {
            "browser": _FakeSkill("browser", ("browser.search", "browser.open")),
            "notes": _FakeSkill("notes", ("notes.write", "notes.read")),
            "notify": _FakeSkill("notify", ("desktop.notify",)),
            "llm": _FakeSkill("llm", ("llm.summarize",)),
        }

    def resolve(self, capability: str):
        # Mirror the native resolver: desktop.notify -> notify skill, etc.
        pid = "notify" if capability == "desktop.notify" else capability.split(".")[0]

        class _R:
            provider_kind = "native"
            provider_id = pid
            available = True
            reason = ""

            @property
            def resolved(self):
                return True

        return _R()

    async def execute_skill(self, name, inputs=None, **_kwargs):
        self.calls.append((name, inputs or {}))
        return await self._skills[name].run(_Ctx(inputs or {}))

    def create_workspace(self, *_a, **_k):
        class _W:
            id = "ws"

        return _W()


class _Ctx:
    def __init__(self, inputs):
        self.inputs = inputs


# ----------------------------------------------------------------- planner


def test_planner_template_match_hackernews() -> None:
    planner = AutonomousPlanner()
    graph = asyncio.run(planner.plan_async("Summarize Hacker News"))
    assert graph.metadata["source"].startswith("template:")
    caps = [t.capability for t in graph.tasks]
    assert "browser.search" in caps
    assert "notes.write" in caps
    assert graph.tasks[1].depends_on == [graph.tasks[0].id]


def test_planner_commit_template() -> None:
    planner = AutonomousPlanner()
    graph = asyncio.run(planner.plan_async("commit my changes with message ship it"))
    assert any(t.capability == "git.commit" for t in graph.tasks)


def test_planner_fallback_without_llm() -> None:
    planner = AutonomousPlanner()
    graph = asyncio.run(planner.plan_async("do something totally novel"))
    assert graph.metadata["source"].startswith("fallback:")
    assert validate_task_graph(graph) == []


def test_planner_llm_fallback_emits_canonical_tasks() -> None:
    async def fake_llm(_prompt: str) -> str:
        return (
            '{"tasks":[{"id":"a","capability":"browser.open",'
            '"action":"open","inputs":{"url":"https://x.com"},'
            '"depends_on":[],"expected_output":"opened"}]}'
        )

    planner = AutonomousPlanner(llm_fn=fake_llm)
    graph = asyncio.run(planner.plan_async("translate this paragraph to french"))
    assert graph.metadata["source"] == "llm"
    assert graph.tasks[0].capability == "browser.open"


def test_validate_detects_cycle() -> None:
    graph = TaskGraph(
        goal="g",
        tasks=[
            Task(id="a", capability="browser.open", depends_on=["b"]),
            Task(id="b", capability="notes.write", depends_on=["a"]),
        ],
    )
    errors = validate_task_graph(graph)
    assert any("cycle" in e for e in errors)


def test_validate_detects_unknown_dependency() -> None:
    graph = TaskGraph(
        goal="g",
        tasks=[Task(id="a", capability="browser.open", depends_on=["missing"])],
    )
    errors = validate_task_graph(graph)
    assert any("unknown task" in e for e in errors)


def test_parse_llm_tasks_strips_fences() -> None:
    raw = '```json\n[{"id":"x","capability":"notes.write","action":"write"}]\n```'
    tasks = _parse_llm_tasks(raw)
    assert tasks
    assert tasks[0].capability == "notes.write"


# ----------------------------------------------------------------- runner


async def test_runner_executes_graph_natively() -> None:
    platform = _FakePlatform()
    planner = AutonomousPlanner()
    runner = NativeGoalRunner(platform, planner)
    goal = type("G", (), {})()  # minimal stand-in; replaced below
    from aios.supervisor import Goal

    goal = Goal(objective="Summarize Hacker News")
    graph = await runner.build_graph(goal.objective)
    await runner.execute(goal, graph)
    # browser + summarize + notes + notify all executed.
    executed = {name for name, _ in platform.calls}
    assert {"browser", "notes", "notify", "llm"} <= executed
    assert goal.context["workflow_result"]["status"] == "completed"


async def test_runner_persists_task_graph_on_goal() -> None:
    platform = _FakePlatform()
    planner = AutonomousPlanner()
    runner = NativeGoalRunner(platform, planner)
    from aios.supervisor import Goal

    goal = Goal(objective="Create a note called Ideas")
    graph = await runner.build_graph(goal.objective)
    await runner.execute(goal, graph)
    assert goal.context["task_graph"]["goal"] == goal.objective


async def test_supervisor_submit_runs_m6_pipeline() -> None:
    platform = _FakePlatform()
    sup = Supervisor(platform)  # type: ignore[arg-type]
    goal = await sup.submit("Summarize Hacker News")
    # Busy-wait for terminal.
    for _ in range(50):
        if goal.is_terminal:
            break
        await asyncio.sleep(0.05)
    assert goal.status.value in ("completed", "failed")
    assert goal.context.get("task_graph") is not None
    assert goal.context["workflow_result"]["status"] == "completed"


# ------------------------------------------------------------------- M6.1


async def _run_with(platform, tasks, *, parallel=True, reflection_fn=None):
    from aios.supervisor import Goal, TaskGraph

    planner = AutonomousPlanner()
    runner = NativeGoalRunner(
        platform, planner, parallel=parallel, reflection_fn=reflection_fn
    )
    graph = TaskGraph(goal="g", tasks=tasks)
    goal = Goal(objective="g")
    await runner.execute(goal, graph)
    return goal


def test_parallel_runs_independent_tasks_concurrently() -> None:
    """Two independent leaves should overlap in wall-clock time."""
    import time

    class _SlowFake(_FakePlatform):
        async def execute_skill(self, name, inputs=None, **_k):
            await asyncio.sleep(0.1)
            return await super().execute_skill(name, inputs=inputs, **_k)

    p = _SlowFake()
    a = Task(id="a", capability="browser.open", action="open", inputs={"url": "x"})
    b = Task(id="b", capability="notes.write", action="write", inputs={"title": "t"})
    c = Task(
        id="c",
        capability="desktop.notify",
        action="notify",
        inputs={"message": "m"},
        depends_on=["a", "b"],
    )
    start = time.monotonic()
    goal = asyncio.run(_run_with(p, [a, b, c]))
    elapsed = time.monotonic() - start
    # a and b run together (~0.1s) then c (~0.1s); serial would be ~0.3s.
    assert elapsed < 0.25, f"expected parallel, got {elapsed:.2f}s"
    assert goal.context["workflow_result"]["status"] == "completed"
    assert {t["id"] for t in goal.context["task_graph"]["tasks"]} == {"a", "b", "c"}


def test_sequential_respects_order_when_disabled() -> None:
    order: list[str] = []

    class _OrderFake(_FakePlatform):
        async def execute_skill(self, name, inputs=None, **_k):
            order.append(name)
            return await super().execute_skill(name, inputs=inputs, **_k)

    p = _OrderFake()
    a = Task(id="a", capability="browser.open", action="open", inputs={"url": "x"})
    b = Task(id="b", capability="notes.write", action="write", inputs={"title": "t"})
    c = Task(
        id="c",
        capability="desktop.notify",
        action="notify",
        inputs={"message": "m"},
        depends_on=["a", "b"],
    )
    goal = asyncio.run(_run_with(p, [a, b, c], parallel=False))
    assert goal.context["workflow_result"]["status"] == "completed"
    # c must run after both a and b.
    assert order.index("notify") > order.index("browser")
    assert order.index("notify") > order.index("notes")


def test_retry_policy_retries_then_succeeds() -> None:
    class _FlakyFake(_FakePlatform):
        def __init__(self):
            super().__init__()
            self.attempts = 0

        async def execute_skill(self, name, inputs=None, **_k):
            self.attempts += 1
            if name == "browser" and self.attempts == 1:
                return SkillResult(status=SkillStatus.FAILED, error="transient")
            return await super().execute_skill(name, inputs=inputs, **_k)

    p = _FlakyFake()
    t = Task(
        id="t",
        capability="browser.open",
        action="open",
        inputs={"url": "x"},
        retry={"max_retries": 2, "backoff_seconds": 0.0},
    )
    goal = asyncio.run(_run_with(p, [t]))
    assert goal.context["workflow_result"]["status"] == "completed"
    assert p.attempts == 2  # first failed, second succeeded
    ev_phases = [e["phase"] for e in goal.context["events"]]
    assert "retry" in ev_phases


def test_reflection_hook_dynamically_replans() -> None:
    """After a step, the reflection hook may append a new task to the graph.

    This exercises M6.1 dynamic replanning: the scheduler re-reads the graph
    each iteration, so a task appended by reflection (with satisfied deps) is
    picked up and executed.
    """
    seen: dict[str, str] = {}

    def reflect(task, output, graph):
        seen[task.id] = output.get("status", "")
        if task.id == "a" and not any(t.id == "extra" for t in graph.tasks):
            graph.tasks.append(
                Task(id="extra", capability="notes.write", action="write",
                     inputs={"title": "added-by-reflection"})
            )

    p = _FakePlatform()
    a = Task(id="a", capability="browser.open", action="open", inputs={"url": "x"})
    b = Task(
        id="b", capability="desktop.notify", action="notify",
        inputs={"message": "m"}, depends_on=["a"],
    )
    goal = asyncio.run(_run_with(p, [a, b], reflection_fn=reflect))
    assert goal.context["workflow_result"]["status"] == "completed"
    # The hook fired for step a, and its dynamic task ran to completion.
    assert str(seen.get("a")) in ("completed", "success")
    executed = {name for name, _ in p.calls}
    assert "notes" in executed  # the reflection-injected task ran
    assert any(t["id"] == "extra" for t in goal.context["task_graph"]["tasks"])
