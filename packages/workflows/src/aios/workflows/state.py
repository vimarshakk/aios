"""WorkflowState — Tracks workflow execution state."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class WorkflowStatus(StrEnum):
    """Overall status of a workflow run."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowState:
    """Mutable state of a running workflow.

    Attributes:
        status: Current workflow status.
        current_step: ID of the step currently executing, or None.
        results: Mapping of step_id → result value.
        step_status: Mapping of step_id → StepStatus string.
        error: Error message if failed.
        created_at: When this state was created.
        updated_at: Last update timestamp.
        metadata: Arbitrary state metadata.
    """

    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: str | None = None
    results: dict[str, Any] = field(default_factory=dict)
    step_status: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = time.time()

    def set_step_status(self, step_id: str, status: str) -> None:
        """Record the status of a step and update timestamp."""
        self.step_status[step_id] = status
        self.touch()

    def mark_running(self, step_id: str) -> None:
        """Mark workflow and a specific step as running."""
        self.status = WorkflowStatus.RUNNING
        self.current_step = step_id
        self.set_step_status(step_id, "running")

    def mark_completed(self, step_id: str, result: Any = None) -> None:
        """Mark a step as completed with its result."""
        self.results[step_id] = result
        self.set_step_status(step_id, "completed")
        self.current_step = None

    def mark_failed(self, step_id: str, error: str) -> None:
        """Mark a step and the workflow as failed."""
        self.status = WorkflowStatus.FAILED
        self.error = error
        self.set_step_status(step_id, "failed")
        self.current_step = None

    def mark_paused(self) -> None:
        """Pause the workflow."""
        self.status = WorkflowStatus.PAUSED
        self.touch()

    def mark_cancelled(self) -> None:
        """Cancel the workflow."""
        self.status = WorkflowStatus.CANCELLED
        self.current_step = None
        self.touch()

    def mark_completed_all(self) -> None:
        """Mark the entire workflow as completed."""
        self.status = WorkflowStatus.COMPLETED
        self.current_step = None
        self.touch()

    def is_terminal(self) -> bool:
        """Return True if the workflow is in a terminal state."""
        return self.status in (
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        )
