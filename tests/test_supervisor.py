"""Tests for the AIOS Supervisor goal orchestration (M6 pipeline, ADR-0024).

Uses a duck-typed ``_FakePlatform`` supporting the post-M6 contract:
``resolve(capability)`` (native-first), ``execute_skill`` (async), and
``create_workspace``. Exercises goal completion, failure, the approval gate,
and pause/cancel through the planner → graph → executor flow.
"""

from __future__ import annotations

import asyncio
from typing import ClassVar

from aios.skills.base import SkillResult, SkillStatus
from aios.supervisor import GoalStatus, Supervisor


class _FakePlatform:
    """Minimal DeveloperPlatform stand-in for Supervisor unit tests."""

    _caps: ClassVar[dict[str, list[str]]] = {}

    def __init__(
        self,
        *,
        fail_skill: str | None = None,
        slow: set[str] | None = None,
    ) -> None:
        self._fail_skill = fail_skill
        self._slow = slow or set()
        self.executed: list[str] = []
        self.created_workspaces: list[str] = []

    def resolve(self, capability: str):
        class _R:
            provider_kind = "native"
            provider_id = capability.split(".")[0]
            available = True
            reason = ""

            @property
            def resolved(self):
                return True

        return _R()

    def create_workspace(self, workspace_id: str, *args, **kwargs) -> object:
        self.created_workspaces.append(workspace_id)

        class _Ws:
            id = workspace_id

        return _Ws()

    async def execute_skill(
        self,
        name: str,
        inputs: dict | None = None,
        workspace_id: str | None = None,
        metadata: dict | None = None,
    ) -> SkillResult:
        self.executed.append(name)
        if name in self._slow:
            await asyncio.sleep(0.15)
        if name == self._fail_skill:
            return SkillResult(status=SkillStatus.FAILED, error=f"{name} failed")
        return SkillResult(
            status=SkillStatus.SUCCESS, data={"skill": name}, steps=[f"ran {name}"]
        )


async def _wait(goal) -> None:
    for _ in range(100):
        await asyncio.sleep(0.01)
        if goal.is_terminal:
            break


async def test_submit_runs_pipeline_to_completion() -> None:
    platform = _FakePlatform()
    sup = Supervisor(platform)
    goal = await sup.submit("open example.com")
    await _wait(goal)
    assert goal.status == GoalStatus.COMPLETED
    assert goal.context.get("task_graph") is not None
    assert platform.created_workspaces == [goal.goal_id]


async def test_failed_step_marks_goal_failed() -> None:
    # The "open" template routes to the browser skill; force it to fail.
    platform = _FakePlatform(fail_skill="browser")
    sup = Supervisor(platform)
    goal = await sup.submit("open example.com")
    await _wait(goal)
    assert goal.status == GoalStatus.FAILED
    assert goal.error is not None


async def test_approval_gate_pauses_without_callback() -> None:
    platform = _FakePlatform()
    sup = Supervisor(platform, require_approval=True, approval_callback=None)
    # Inject a planner that emits a sensitive (destructive) capability so the
    # approval gate engages.
    from aios.supervisor import AutonomousPlanner, Task, TaskGraph

    class _SensitivePlanner(AutonomousPlanner):
        async def plan_async(self, goal, capabilities=None):
            return TaskGraph(
                goal=goal,
                tasks=[Task(id="x", capability="destructive:delete", action="delete")],
            )

    sup.planner = _SensitivePlanner()
    sup.runner.planner = _SensitivePlanner()
    goal = await sup.submit("delete my Downloads folder")
    await _wait(goal)
    # No callback -> paused awaiting resume / waiting approval.
    assert goal.status in (GoalStatus.WAITING_APPROVAL, GoalStatus.PAUSED)


async def test_pause_and_cancel() -> None:
    platform = _FakePlatform(slow={"browser"})
    sup = Supervisor(platform)
    goal = await sup.submit("open example.com")
    await asyncio.sleep(0.05)
    assert await sup.pause(goal.goal_id) is True
    assert goal.status == GoalStatus.PAUSED
    assert await sup.cancel(goal.goal_id) is True
    assert goal.status == GoalStatus.CANCELLED


def test_goal_progress_empty() -> None:
    from aios.supervisor import Goal

    g = Goal(objective="nothing")
    assert g.progress()["percent"] == 100
    assert g.is_terminal is False
