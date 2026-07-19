"""Core workflow types — WorkflowStep, Workflow, WorkflowResult."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class StepStatus(StrEnum):
    """Status of a single workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"
    BLOCKED = "blocked"


@dataclass
class WorkflowStep:
    """A single step in a workflow.

    Attributes:
        id: Unique identifier for this step.
        type: Step type — "agent_call", "tool_call", "condition", "approval", "parallel".
        config: Arbitrary configuration dict consumed by the executor.
        dependencies: IDs of steps that must complete before this step runs.
        retry: Optional retry policy for transient failures.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: str = "tool_call"
    config: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = uuid.uuid4().hex[:12]


@dataclass
class WorkflowResult:
    """Outcome of executing a workflow.

    Attributes:
        workflow_id: ID of the workflow that produced this result.
        status: Final workflow status (completed, failed, cancelled).
        step_results: Mapping of step ID → step output.
        error: Error message if the workflow failed.
        started_at: Timestamp when execution started.
        finished_at: Timestamp when execution finished.
    """

    workflow_id: str
    status: str
    step_results: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    @property
    def duration(self) -> float | None:
        """Return duration in seconds, or None if not finished."""
        if self.finished_at is None:
            return None
        return self.finished_at - self.started_at


@dataclass
class Workflow:
    """A complete workflow with named steps and metadata.

    Attributes:
        id: Unique workflow identifier.
        name: Human-readable name.
        steps: Ordered list of workflow steps.
        metadata: Arbitrary metadata (tags, owner, version, etc.).
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "unnamed"
    steps: list[WorkflowStep] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_step(self, step_id: str) -> WorkflowStep | None:
        """Look up a step by ID."""
        for s in self.steps:
            if s.id == step_id:
                return s
        return None

    def get_step_index(self, step_id: str) -> int:
        """Return the index of a step, or -1 if not found."""
        for i, s in enumerate(self.steps):
            if s.id == step_id:
                return i
        return -1

    def steps_by_status(self, status: StepStatus, results: dict[str, Any]) -> list[WorkflowStep]:
        """Return steps whose status matches, based on the results dict.

        The results dict maps step_id → StepStatus (or result value).
        This is a convenience for the executor.
        """
        out: list[WorkflowStep] = []
        for s in self.steps:
            r = results.get(s.id)
            if isinstance(r, StepStatus) and r == status:
                out.append(s)
        return out
