"""WorkflowEventBus — Event-driven hooks for workflow lifecycle."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class WorkflowEventType(StrEnum):
    """Types of workflow lifecycle events."""

    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_RETRYING = "step_retrying"
    STEP_SKIPPED = "step_skipped"
    CONDITION_EVALUATED = "condition_evaluated"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RESOLVED = "approval_resolved"


@dataclass(frozen=True)
class WorkflowEvent:
    """Immutable event emitted during workflow execution.

    Attributes:
        event_type: The type of lifecycle event.
        workflow_id: ID of the workflow.
        step_id: ID of the step (if step-level event).
        data: Arbitrary event payload.
    """

    event_type: WorkflowEventType
    workflow_id: str
    step_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


EventHandler = Callable[[WorkflowEvent], Any]


class WorkflowEventBus:
    """In-process event bus for workflow lifecycle hooks.

    Handlers are called in order of registration. Async handlers are
    awaited; sync handlers are called directly. Exceptions in handlers
    are collected but do not abort the workflow.

    Usage::

        bus = WorkflowEventBus()
        bus.on(WorkflowEventType.STEP_STARTED, my_handler)
        bus.emit(WorkflowEvent(event_type=..., workflow_id="w1"))
    """

    def __init__(self) -> None:
        self._handlers: dict[WorkflowEventType, list[EventHandler]] = {}
        self._history: list[WorkflowEvent] = []
        self._pending_tasks: set[asyncio.Task[None]] = set()

    def on(self, event_type: WorkflowEventType, handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        self._handlers.setdefault(event_type, []).append(handler)

    def off(self, event_type: WorkflowEventType, handler: EventHandler) -> bool:
        """Remove a handler. Returns True if it was found and removed."""
        handlers = self._handlers.get(event_type, [])
        try:
            handlers.remove(handler)
            return True
        except ValueError:
            return False

    def clear(self) -> None:
        """Remove all handlers and event history."""
        self._handlers.clear()
        self._history.clear()

    def emit(self, event: WorkflowEvent) -> None:
        """Emit an event, calling all registered handlers synchronously.

        Async handlers are scheduled on the running event loop; if no
        loop is running they are silently skipped.
        """
        self._history.append(event)
        for handler in self._handlers.get(event.event_type, []):
            with contextlib.suppress(Exception):
                result = handler(event)
                if asyncio.isfuture(result) or asyncio.iscoroutine(result):
                    with contextlib.suppress(RuntimeError):
                        loop = asyncio.get_running_loop()
                        task = loop.create_task(self._safe_async(handler, event))
                        self._pending_tasks.add(task)
                        task.add_done_callback(self._pending_tasks.discard)

    async def _safe_async(self, handler: EventHandler, event: WorkflowEvent) -> None:
        """Wrap async handler call to catch errors."""
        with contextlib.suppress(Exception):
            await handler(event)  # type: ignore[misc]

    @property
    def history(self) -> list[WorkflowEvent]:
        """Return all emitted events (read-only copy)."""
        return list(self._history)

    def events_for_workflow(self, workflow_id: str) -> list[WorkflowEvent]:
        """Return events for a specific workflow."""
        return [e for e in self._history if e.workflow_id == workflow_id]
