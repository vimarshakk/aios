"""Human-in-the-loop approval steps."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from aios.workflows.base import WorkflowStep

if TYPE_CHECKING:
    from collections.abc import Callable


class ApprovalStatus(StrEnum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    """Represents a pending human approval.

    Attributes:
        step_id: The workflow step requesting approval.
        prompt: Human-readable description of what needs approval.
        context: Additional context (proposed action, risk level, etc.).
        status: Current approval status.
        approver: Who approved/rejected, if anyone.
        timeout_seconds: How long to wait before expiring (None = wait forever).
        response: The approver's response message, if any.
    """

    step_id: str
    prompt: str
    context: dict[str, Any] = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver: str | None = None
    timeout_seconds: float | None = 300.0
    response: str | None = None

    def approve(self, approver: str = "user", response: str | None = None) -> None:
        """Mark this request as approved."""
        self.status = ApprovalStatus.APPROVED
        self.approver = approver
        self.response = response

    def reject(self, approver: str = "user", response: str | None = None) -> None:
        """Mark this request as rejected."""
        self.status = ApprovalStatus.REJECTED
        self.approver = approver
        self.response = response

    def is_resolved(self) -> bool:
        """Return True if the approval is in a terminal state."""
        return self.status in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.EXPIRED,
        )


@dataclass
class ApprovalStep(WorkflowStep):
    """A workflow step that pauses execution and waits for human approval.

    The executor should:
    1. Create an ApprovalRequest when encountering this step.
    2. Pause the workflow.
    3. Wait for the approval to be resolved (approve/reject/timeout).
    4. Resume or abort based on the outcome.
    """

    prompt: str = ""
    timeout_seconds: float | None = 300.0
    require_response: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        self.type = "approval"

    def create_request(self) -> ApprovalRequest:
        """Create an ApprovalRequest from this step's config."""
        return ApprovalRequest(
            step_id=self.id,
            prompt=self.prompt or self.config.get("prompt", "Approval required"),
            context=self.config.get("context", {}),
            timeout_seconds=self.timeout_seconds,
        )


async def wait_for_approval(
    request: ApprovalRequest,
    callback: Callable[[ApprovalRequest], None] | None = None,
) -> ApprovalRequest:
    """Wait for an ApprovalRequest to be resolved.

    This polls the request's status until it is resolved or timed out.
    In a real system, this would use an event bus or websocket.

    Args:
        request: The ApprovalRequest to wait on.
        callback: Optional callback invoked when the request is created (e.g. to notify UI).

    Returns:
        The resolved ApprovalRequest.
    """
    if callback is not None:
        callback(request)

    start = request._start_time if hasattr(request, "_start_time") else None

    # Poll loop — in production this would be event-driven
    while not request.is_resolved():
        await asyncio.sleep(0.1)
        if request.timeout_seconds is not None and start is not None:
            import time

            if time.time() - start > request.timeout_seconds:
                request.status = ApprovalStatus.EXPIRED
                break

    return request
