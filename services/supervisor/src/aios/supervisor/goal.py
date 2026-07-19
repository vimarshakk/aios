"""Goal state model for the AIOS Supervisor.

The Supervisor owns long-running execution. A :class:`Goal` is a user objective
that gets decomposed into a :class:`~aios.skills.planner.SkillPlan` and executed
step by step. :class:`GoalState` tracks progress, supports pause/resume, and
records per-step outcomes so a goal can be safely interrupted and resumed.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class GoalStatus(StrEnum):
    """Lifecycle status of a supervised goal."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepOutcome(StrEnum):
    """Outcome of an individual goal step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"


@dataclass
class StepRecord:
    """Record of a single planned step's execution."""

    step_index: int
    skill: str
    status: StepOutcome = StepOutcome.PENDING
    result: Any = None
    error: str | None = None
    started_at: float | None = None
    finished_at: float | None = None
    attempts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "skill": self.skill,
            "status": self.status.value,
            "error": self.error,
            "attempts": self.attempts,
        }


@dataclass
class Goal:
    """A user objective being executed under supervision."""

    objective: str
    goal_id: str = field(default_factory=lambda: f"goal-{uuid.uuid4().hex[:12]}")
    status: GoalStatus = GoalStatus.PENDING
    created_at: float = field(default_factory=time.monotonic)
    steps: list[StepRecord] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            GoalStatus.COMPLETED,
            GoalStatus.FAILED,
            GoalStatus.CANCELLED,
        )

    def step_at(self, index: int) -> StepRecord | None:
        try:
            return self.steps[index]
        except IndexError:
            return None

    def next_pending_index(self) -> int | None:
        for i, step in enumerate(self.steps):
            if step.status in (StepOutcome.PENDING, StepOutcome.FAILED):
                return i
        return None

    def progress(self) -> dict[str, Any]:
        total = len(self.steps)
        done = sum(1 for s in self.steps if s.status == StepOutcome.SUCCESS)
        failed = sum(1 for s in self.steps if s.status == StepOutcome.FAILED)
        return {
            "goal_id": self.goal_id,
            "status": self.status.value,
            "total_steps": total,
            "completed": done,
            "failed": failed,
            "percent": round(100.0 * done / total) if total else 100,
        }

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "goal_id": self.goal_id,
            "objective": self.objective,
            "status": self.status.value,
            "progress": self.progress(),
            "steps": [s.to_dict() for s in self.steps],
            "artifacts": list(self.artifacts),
            "error": self.error,
        }
        # M6 autonomous pipeline view (persisted task graph + lifecycle events).
        if self.context.get("task_graph"):
            data["task_graph"] = self.context["task_graph"]
        if self.context.get("events"):
            data["events"] = self.context["events"]
        if self.context.get("workflow_result"):
            data["workflow_result"] = self.context["workflow_result"]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Goal:
        """Reconstruct a Goal from ``to_dict()`` output.

        Used by the daemon to restore persisted goals across restarts. The
        restored goal is terminal (already executed) — its live execution
        coroutine is gone, so it is reattached read-only rather than re-run.
        """
        goal = cls(objective=data.get("objective", ""))
        goal.goal_id = data.get("goal_id", goal.goal_id)
        goal.status = GoalStatus(data.get("status", "completed"))
        goal.artifacts = list(data.get("artifacts", []))
        goal.error = data.get("error")
        goal.steps = [_step_from_dict(s) for s in data.get("steps", [])]
        context = goal.context
        if data.get("task_graph"):
            context["task_graph"] = data["task_graph"]
        if data.get("events"):
            context["events"] = data["events"]
        if data.get("workflow_result"):
            context["workflow_result"] = data["workflow_result"]
        return goal


def _step_from_dict(s: dict[str, Any]) -> StepRecord:
    """Rebuild a StepRecord, tolerating the serialised (str) status value."""
    status = s.get("status", "pending")
    if not isinstance(status, StepOutcome):
        status = StepOutcome(status)
    return StepRecord(
        step_index=s.get("step_index", 0),
        skill=s.get("skill", ""),
        status=status,
        result=s.get("result"),
        error=s.get("error"),
        attempts=s.get("attempts", 0),
    )


__all__ = ["Goal", "GoalStatus", "StepOutcome", "StepRecord"]
