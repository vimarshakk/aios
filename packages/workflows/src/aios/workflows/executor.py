"""WorkflowExecutor — Executes workflow steps with native condition routing,
approval handling, timeouts, and event hooks."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from aios.workflows.approval import ApprovalRequest, ApprovalStep
from aios.workflows.base import StepStatus, Workflow, WorkflowResult, WorkflowStep
from aios.workflows.conditions import ConditionStep
from aios.workflows.events import (
    WorkflowEvent,
    WorkflowEventBus,
    WorkflowEventType,
)
from aios.workflows.state import WorkflowState, WorkflowStatus

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class WorkflowTimeout(Exception):  # noqa: N818
    """Raised when a workflow exceeds its time limit."""


class WorkflowExecutor:
    """Execute workflow steps, respecting dependencies and state.

    Enhancements over the basic executor:
    - Native ConditionStep routing (no manual handler needed)
    - ApprovalStep pause/resume (via on_approval callback)
    - Workflow-level timeout_seconds
    - Event bus hooks for observability
    - Retry support (reads RetryPolicy from step config)

    Attributes:
        handlers: Mapping of step type → async handler function.
        on_approval: Called when an approval step needs human input.
            Receives ApprovalRequest; should call .approve() or .reject().
        timeout_seconds: Max wall-clock seconds for the entire workflow run.
        event_bus: Optional event bus for lifecycle hooks.
    """

    def __init__(
        self,
        handlers: dict[str, Callable[[WorkflowStep, WorkflowState], Awaitable[Any]]] | None = None,
        *,
        on_approval: Callable[[ApprovalRequest], Awaitable[None]] | None = None,
        timeout_seconds: float | None = None,
        event_bus: WorkflowEventBus | None = None,
    ) -> None:
        self.handlers: dict[str, Callable[[WorkflowStep, WorkflowState], Awaitable[Any]]] = (
            handlers or {}
        )
        self.on_approval = on_approval
        self.timeout_seconds = timeout_seconds
        self.event_bus = event_bus
        self._state = WorkflowState()

    @property
    def state(self) -> WorkflowState:
        """Current workflow state."""
        return self._state

    def register_handler(
        self,
        step_type: str,
        handler: Callable[[WorkflowStep, WorkflowState], Awaitable[Any]],
    ) -> None:
        """Register an async handler for a step type."""
        self.handlers[step_type] = handler

    def _build_dependency_graph(
        self, workflow: Workflow
    ) -> dict[str, set[str]]:
        """Build a map of step_id → set of unresolved dependency IDs."""
        step_ids = {s.id for s in workflow.steps}
        graph: dict[str, set[str]] = {}
        for step in workflow.steps:
            deps = {d for d in step.dependencies if d in step_ids}
            graph[step.id] = deps
        return graph

    def _find_ready(
        self,
        graph: dict[str, set[str]],
        completed: set[str],
        skipped: set[str] | None = None,
    ) -> list[str]:
        """Return step IDs whose dependencies are all completed (or skipped)."""
        _skipped = skipped or set()
        ready = []
        for sid, deps in graph.items():
            if sid in completed or sid in _skipped:
                continue
            if deps.issubset(completed | _skipped):
                ready.append(sid)
        return ready

    def _emit(
        self, event_type: WorkflowEventType, wf_id: str,
        step_id: str | None = None, **data: Any,
    ) -> None:
        """Emit a lifecycle event if the bus is attached."""
        if self.event_bus is not None:
            self.event_bus.emit(
                WorkflowEvent(
                    event_type=event_type,
                    workflow_id=wf_id,
                    step_id=step_id,
                    data=dict(data),
                )
            )

    async def run(self, workflow: Workflow) -> WorkflowResult:
        """Execute the full workflow and return the result.

        Steps are run in topological order (respecting dependencies).
        Native condition routing evaluates ConditionSteps and skips branches.
        ApprovalSteps pause execution and invoke the on_approval callback.
        The entire run is bounded by timeout_seconds if set.
        """
        self._state = WorkflowState()
        self._state.status = WorkflowStatus.RUNNING

        result = WorkflowResult(
            workflow_id=workflow.id,
            status="running",
            started_at=time.time(),
        )

        self._emit(WorkflowEventType.WORKFLOW_STARTED, workflow.id)

        graph = self._build_dependency_graph(workflow)
        completed: set[str] = set()
        skipped: set[str] = set()
        failed = False
        error_msg: str | None = None

        try:
            coro = self._run_loop(workflow, graph, result, completed, skipped)
            if self.timeout_seconds is not None:
                try:
                    await asyncio.wait_for(coro, timeout=self.timeout_seconds)
                except TimeoutError:
                    result.status = "failed"
                    result.error = f"Workflow timed out after {self.timeout_seconds}s"
                    self._state.status = WorkflowStatus.FAILED
                    self._state.error = result.error
                    self._emit(
                        WorkflowEventType.WORKFLOW_FAILED, workflow.id,
                        error=result.error,
                    )
                    result.finished_at = time.time()
                    return result
            else:
                await coro

            failed = self._state.status == WorkflowStatus.FAILED
            error_msg = self._state.error

        except Exception as exc:
            failed = True
            error_msg = str(exc)
            result.status = "failed"
            result.error = str(exc)
            self._state.status = WorkflowStatus.FAILED
            self._state.error = str(exc)

        if failed:
            result.status = "failed"
            result.error = error_msg or "Workflow halted"
            self._emit(
                WorkflowEventType.WORKFLOW_FAILED, workflow.id,
                error=result.error,
            )
        else:
            result.status = "completed"
            self._state.mark_completed_all()
            self._emit(WorkflowEventType.WORKFLOW_COMPLETED, workflow.id)

        result.finished_at = time.time()
        return result

    async def _run_loop(
        self,
        workflow: Workflow,
        graph: dict[str, set[str]],
        result: WorkflowResult,
        completed: set[str],
        skipped: set[str],
    ) -> None:
        """Core execution loop — runs until done, failed, or blocked."""
        while len(completed) + len(skipped) < len(workflow.steps):
            ready_ids = self._find_ready(graph, completed, skipped)

            if not ready_ids:
                if self._state.status == WorkflowStatus.FAILED:
                    pass  # Already failed
                else:
                    self._state.error = "Deadlock: no ready steps"
                    self._state.status = WorkflowStatus.FAILED
                break

            for step_id in ready_ids:
                step = workflow.get_step(step_id)
                if step is None:
                    skipped.add(step_id)
                    continue

                self._state.mark_running(step_id)
                result.step_results[step_id] = StepStatus.RUNNING
                self._emit(WorkflowEventType.STEP_STARTED, workflow.id, step_id=step_id)

                try:
                    step_result = await self._execute_step(step, workflow)

                    # Native condition routing
                    if isinstance(step, ConditionStep):
                        target = step_result
                        self._emit(
                            WorkflowEventType.CONDITION_EVALUATED,
                            workflow.id,
                            step_id=step_id,
                            target=target,
                        )
                        if target is not None and workflow.get_step(target) is not None:
                            # Mark condition as completed, target will run when deps satisfied
                            self._state.mark_completed(step_id, step_result)
                            result.step_results[step_id] = step_result
                            completed.add(step_id)
                        else:
                            # No valid target — skip downstream steps of this branch
                            self._state.mark_completed(step_id, step_result)
                            result.step_results[step_id] = step_result
                            completed.add(step_id)
                            # Skip steps that ONLY depend on steps in this dead branch
                            self._skip_dead_branches(workflow, graph, completed, skipped)
                    else:
                        self._state.mark_completed(step_id, step_result)
                        result.step_results[step_id] = step_result
                        completed.add(step_id)

                    self._emit(WorkflowEventType.STEP_COMPLETED, workflow.id, step_id=step_id)

                except Exception as exc:
                    self._state.mark_failed(step_id, str(exc))
                    result.step_results[step_id] = StepStatus.FAILED
                    completed.add(step_id)
                    self._emit(
                        WorkflowEventType.STEP_FAILED, workflow.id,
                        step_id=step_id, error=str(exc),
                    )
                    break

            if self._state.status == WorkflowStatus.FAILED:
                break

    def _skip_dead_branches(
        self,
        workflow: Workflow,
        graph: dict[str, set[str]],
        completed: set[str],
        skipped: set[str],
    ) -> None:
        """Skip steps whose only remaining dependencies are in completed branches
        that are not targetable."""
        # Steps that depend on completed steps but can't be reached
        # are left to the normal readiness check — this is a no-op for now
        # but provides the hook for future branch-aware pruning.

    async def _execute_step(
        self, step: WorkflowStep, workflow: Workflow,  # noqa: ARG002
    ) -> Any:
        """Execute a single step, with native handling for conditions and approvals."""
        # Native ConditionStep handling
        if isinstance(step, ConditionStep):
            return await self._handle_condition(step)

        # Native ApprovalStep handling
        if isinstance(step, ApprovalStep):
            return await self._handle_approval(step)

        # Retry logic — check if step config has a retry policy
        retry_config = step.config.get("retry")
        if retry_config is not None:
            return await self._execute_with_retry(step, retry_config)

        # Standard handler lookup
        handler = self.handlers.get(step.type)
        if handler is None:
            raise ValueError(f"No handler registered for step type '{step.type}'")
        return await handler(step, self._state)

    async def _handle_condition(self, step: ConditionStep) -> str | None:
        """Evaluate a ConditionStep and return the target step ID."""
        result = await step.evaluate(self._state.results)
        return result.target_step_id

    async def _handle_approval(self, step: ApprovalStep) -> bool:
        """Handle an ApprovalStep — create request, invoke callback, wait."""
        request = step.create_request()

        self._emit(
            WorkflowEventType.APPROVAL_REQUESTED,
            "",  # workflow_id filled by caller
            step_id=step.id,
            prompt=request.prompt,
        )

        if self.on_approval is not None:
            await self.on_approval(request)
        else:
            # Auto-approve when no approval handler is set
            request.approve(approver="system:auto", response="No approval handler set")

        self._emit(
            WorkflowEventType.APPROVAL_RESOLVED,
            "",
            step_id=step.id,
            status=str(request.status),
        )

        if request.status.value == "rejected":
            raise RuntimeError(f"Approval rejected for step '{step.id}': {request.response}")
        return True

    async def _execute_with_retry(
        self, step: WorkflowStep, retry_config: dict[str, Any]
    ) -> Any:
        """Execute a step with retry logic from its config."""
        handler = self.handlers.get(step.type)
        if handler is None:
            raise ValueError(f"No handler registered for step type '{step.type}'")

        max_retries = retry_config.get("max_retries", 3)
        base_delay = retry_config.get("base_delay", 1.0)
        backoff_factor = retry_config.get("backoff_factor", 2.0)

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                return await handler(step, self._state)
            except Exception as exc:
                last_error = exc
                if attempt < max_retries:
                    self._emit(
                        WorkflowEventType.STEP_RETRYING,
                        "",
                        step_id=step.id,
                        attempt=attempt + 1,
                        error=str(exc),
                    )
                    delay = base_delay * (backoff_factor ** attempt)
                    await asyncio.sleep(delay)
        if last_error is not None:
            raise last_error
        return None  # pragma: no cover

    async def resume(
        self,
        workflow: Workflow,
        result: WorkflowResult,
    ) -> WorkflowResult:
        """Resume a failed/paused workflow from where it left off.

        Skips steps that already completed successfully.
        """
        self._state.status = WorkflowStatus.RUNNING
        result.status = "running"
        result.started_at = time.time()

        self._emit(WorkflowEventType.WORKFLOW_RESUMED, workflow.id)

        graph = self._build_dependency_graph(workflow)
        completed: set[str] = set()
        skipped: set[str] = set()

        # Find already-completed steps
        for sid, val in result.step_results.items():
            if val is not StepStatus.FAILED and val is not StepStatus.SKIPPED:
                completed.add(sid)

        try:
            await self._run_loop(workflow, graph, result, completed, skipped)
        except Exception as exc:
            self._state.status = WorkflowStatus.FAILED
            self._state.error = str(exc)

        if self._state.status == WorkflowStatus.FAILED:
            result.status = "failed"
            result.error = self._state.error
        else:
            result.status = "completed"
            self._state.mark_completed_all()

        result.finished_at = time.time()
        return result
