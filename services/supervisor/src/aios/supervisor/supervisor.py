"""AIOS Supervisor — top-level long-running goal orchestration.

The Supervisor is the composition root for autonomous goal execution. It does
not reimplement planning, scheduling, skills, permissions, or connectors; it
composes the existing platform primitives (ADR-0019 / ADR-0021):

    User → Supervisor → Planner (capability plan)
         → Task Graph (SkillPlan steps)
         → Agent/Skill Scheduler (DeveloperPlatform.execute_skill)
         → Connectors (Composio + builtins via skills)
         → Verification (SkillResult / policy)
         → Memory (workspace artifacts + execution history)
         → Response

Key responsibilities added by the Supervisor (and only these):
- Owning the goal lifecycle (pause / resume / cancel / retry).
- Gating each step through the platform policy before execution.
- Pausing for human approval when a step is flagged required-approval.
- Recording every step outcome into the goal state and a workspace.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .executor import ApprovalRequiredError
from .goal import Goal, GoalStatus, StepOutcome, StepRecord

_ApprovalRequired = ApprovalRequiredError

if TYPE_CHECKING:
    from aios.platform import DeveloperPlatform

logger = logging.getLogger("aios.supervisor")

ApprovalCallback = Callable[["ApprovalRequest"], Awaitable[bool]]
LLMFn = Callable[[str], Awaitable[str]]


@dataclass
class ApprovalRequest:
    """A request for human approval before a sensitive step executes."""

    goal_id: str
    step_index: int
    skill: str
    capabilities: list[str]
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "step_index": self.step_index,
            "skill": self.skill,
            "capabilities": self.capabilities,
            "reason": self.reason,
        }


# Steps whose skills match these capability prefixes pause for approval.
_APPROVAL_CAPABILITY_PREFIXES = ("external:", "destructive:", "publish:")


class Supervisor:
    """Execute user goals as supervised, resumable skill plans."""

    def __init__(
        self,
        platform: DeveloperPlatform,
        *,
        max_step_attempts: int = 3,
        approval_callback: ApprovalCallback | None = None,
        require_approval: bool = True,
        llm_fn: LLMFn | None = None,
        planner_timeout_seconds: float | None = None,
        parallel: bool = True,
        reflection_fn: Any | None = None,
        on_goal_update: Any | None = None,
    ) -> None:
        """Build a Supervisor around a :class:`DeveloperPlatform`.

        Args:
            platform: Composition root exposing ``plan``, ``execute_skill``,
                ``authorize``, ``resolve``, and ``create_workspace``.
            max_step_attempts: Legacy retry knob (retained for compatibility;
                M6.1 per-task retry is driven by ``Task.retry`` from the planner).
            approval_callback: Async callable deciding approval requests. When
                ``None`` and approval is required, the goal waits in
                ``WAITING_APPROVAL`` until ``resume`` is called.
            require_approval: Gate sensitive steps behind approval.
            llm_fn: Optional async callable used by the M6 planner to decompose
                unknown goals. When ``None``, the planner uses deterministic
                templates and offline fallbacks only.
            planner_timeout_seconds: Bound for a single goal's execution.
            parallel: Run independent ready-set tasks concurrently (M6.1).
            reflection_fn: Optional hook ``(task, output, graph)`` invoked after
                each reflected step; may mutate ``graph`` for self-correction.
            on_goal_update: Optional callback invoked whenever a goal transitions
                to a terminal state (completed/failed/cancelled). Used by the
                daemon to persist the final goal state; must not raise.
        """
        from .executor import NativeGoalRunner
        from .planner import AutonomousPlanner

        self.platform = platform
        self.max_step_attempts = max_step_attempts
        self.approval_callback = approval_callback
        self.require_approval = require_approval
        self.on_goal_update = on_goal_update
        self._goals: dict[str, Goal] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        # (goal_id, step_index) pairs pre-approved (e.g. via human resume).
        self._approved: set[tuple[str, int]] = set()

        # M6 — autonomous planner + native executor (ADR-0024 / M6.1).
        self.planner = AutonomousPlanner(llm_fn=llm_fn)
        self.runner = NativeGoalRunner(
            platform,
            self.planner,
            require_approval=require_approval,
            approval_callback=approval_callback,
            timeout_seconds=planner_timeout_seconds,
            parallel=parallel,
            reflection_fn=reflection_fn,
        )

    # ----------------------------------------------------------------- discovery

    def list_goals(self) -> list[dict[str, Any]]:
        return [g.to_dict() for g in self._goals.values()]

    def get_goal(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    def restore_goals(self, goals: list[Goal]) -> None:
        """Re-attach previously persisted goals (e.g. after a daemon restart).

        Restored goals are kept read-only: their execution coroutine no longer
        exists, so we must not re-run them — only make their recorded state
        (status, steps, artifacts) queryable again.
        """
        for g in goals:
            self._goals.setdefault(g.goal_id, g)

    def _lock_for(self, goal_id: str) -> asyncio.Lock:
        lock = self._locks.get(goal_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[goal_id] = lock
        return lock

    # --------------------------------------------------------------- submission

    async def submit(
        self,
        objective: str,
        *,
        capabilities: list[str] | None = None,
        workspace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Goal:
        """Submit a new goal: decompose it with the M6 planner, then execute.

        Returns the tracked :class:`Goal`. The planned task graph is persisted on
        the goal (survives daemon restart) and execution runs as a background
        task. Inspect ``goal.status`` / ``goal.to_dict()`` for live state and the
        ``task_graph`` / ``events`` keys for the autonomous pipeline view.
        """
        goal = Goal(objective=objective, status=GoalStatus.PENDING)
        self._goals[goal.goal_id] = goal
        goal.context["metadata"] = metadata or {}
        if workspace_id is None:
            workspace_id = self.platform.create_workspace(goal.goal_id, root=".").id
        goal.context["workspace_id"] = workspace_id

        self._tasks[goal.goal_id] = asyncio.create_task(
            self._run_goal(goal, capabilities=capabilities)
        )
        return goal

    # ----------------------------------------------------------------- execution

    async def _run_goal(
        self,
        goal: Goal,
        *,
        capabilities: list[str] | None = None,
    ) -> None:
        goal.status = GoalStatus.RUNNING
        try:
            # Reuse the already-planned graph on resume; otherwise plan fresh.
            existing = goal.context.get("task_graph")
            if existing:
                from .task_graph import TaskGraph

                graph = TaskGraph.from_dict(existing)
            else:
                graph = await self.runner.build_graph(goal.objective, capabilities)
                goal.context["task_graph"] = graph.to_dict()
                goal.steps = [
                    StepRecord(step_index=i, skill=t.capability)
                    for i, t in enumerate(graph.tasks)
                ]
            await self.runner.execute(goal, graph, workspace_id=goal.context.get("workspace_id"))
            result = goal.context.get("workflow_result", {})
            if result.get("status") == "completed":
                goal.status = GoalStatus.COMPLETED
            elif result.get("status") == "failed":
                goal.status = GoalStatus.FAILED
                goal.error = result.get("error")
            else:
                goal.status = GoalStatus.COMPLETED
            if self.on_goal_update is not None:
                self.on_goal_update(goal)
        except _ApprovalRequired as exc:
            # Sensitive step awaiting human approval (no automated approver).
            goal.status = GoalStatus.WAITING_APPROVAL
            goal.error = str(exc)
        except Exception as exc:  # surface as goal failure
            logger.exception("Goal %s failed with unexpected error", goal.goal_id)
            goal.status = GoalStatus.FAILED
            goal.error = str(exc)

    def _needs_approval(self, capabilities: list[str]) -> bool:
        return any(
            cap.startswith(prefix) for cap in capabilities
            for prefix in _APPROVAL_CAPABILITY_PREFIXES
        )

    async def _request_approval(
        self, goal: Goal, index: int, skill: str, caps: list[str]
    ) -> bool:
        if self.approval_callback is None:
            return False
        request = ApprovalRequest(
            goal_id=goal.goal_id,
            step_index=index,
            skill=skill,
            capabilities=caps,
            reason="Sensitive capability requires approval.",
        )
        try:
            return bool(await self.approval_callback(request))
        except Exception:  # treat callback failure as deny
            logger.exception("Approval callback raised; denying step")
            return False

    # ----------------------------------------------------------------- control

    async def pause(self, goal_id: str) -> bool:
        goal = self._goals.get(goal_id)
        if goal is None or goal.is_terminal:
            return False
        goal.status = GoalStatus.PAUSED
        return True

    async def cancel(self, goal_id: str) -> bool:
        goal = self._goals.get(goal_id)
        if goal is None or goal.is_terminal:
            return False
        goal.status = GoalStatus.CANCELLED
        return True

    async def resume(self, goal_id: str) -> bool:
        """Resume a paused / waiting-approval goal from where it stopped."""
        goal = self._goals.get(goal_id)
        if goal is None or goal.is_terminal:
            return False
        if goal.status not in (GoalStatus.PAUSED, GoalStatus.WAITING_APPROVAL):
            return False
        # Pre-approve any steps that were waiting, simulating a human approval,
        # and reset them so they execute on the resumed run.
        for step in goal.steps:
            if step.status == StepOutcome.WAITING_APPROVAL:
                step.status = StepOutcome.PENDING
                self._approved.add((goal.goal_id, step.step_index))
        self._tasks[goal.goal_id] = asyncio.create_task(self._run_goal(goal))
        return True


__all__ = ["ApprovalRequest", "Supervisor"]
