"""M6.1 executor — run a canonical TaskGraph as native skills via the platform.

This module is the bridge between the planner's typed DAG and the live
:class:`~aios.platform.DeveloperPlatform`: every step is mapped through the
:class:`~aios.platform.CapabilityResolver` (native-first) and executed with
``platform.execute_skill``.

M6.1 adds three robustness capabilities on top of the core M6 pipeline:

* **Parallel execution** — independent ready-set steps run concurrently via
  :func:`asyncio.gather`; dependents wait for their predecessors.
* **Retry policies** — a task may carry ``retry={"max_retries": n,
  "backoff_seconds": s}``; the runner retries failed attempts with backoff.
* **Reflection** — after each step, an optional ``reflection_fn`` inspects the
  step outcome (and the running graph) and may rewrite the graph for
  self-correction (M6.1 dynamic replanning hook).

The runner persists the planned graph onto the :class:`~aios.supervisor.goal.Goal`
and pushes step lifecycle events into a per-goal event log that the existing
WebSocket endpoint streams. Progress survives daemon restarts because the graph
is part of the goal state.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .goal import StepOutcome
from .task_graph import Task, TaskGraph, validate_task_graph

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aios.platform import DeveloperPlatform

    from .goal import Goal
    from .planner import AutonomousPlanner

# Capabilities that require human approval before execution (mirrors
# Supervisor._APPROVAL_CAPABILITY_PREFIXES for parity with M5).
_APPROVAL_PREFIXES = ("external:", "destructive:", "publish:")


class ApprovalRequiredError(RuntimeError):
    """Raised when a sensitive step needs human approval that was not granted."""


# Signature: reflection_fn(task, output, graph) -> None  (may mutate graph)
ReflectionFn = Callable[[Task, dict[str, Any], TaskGraph], Any]


class NativeGoalRunner:
    """Plan, validate, and execute a goal as native skills on the platform."""

    def __init__(
        self,
        platform: DeveloperPlatform,
        planner: AutonomousPlanner,
        *,
        require_approval: bool = True,
        approval_callback: Any | None = None,
        timeout_seconds: float | None = None,
        parallel: bool = True,
        reflection_fn: ReflectionFn | None = None,
    ) -> None:
        self.platform = platform
        self.planner = planner
        self.require_approval = require_approval
        self.approval_callback = approval_callback
        self.timeout_seconds = timeout_seconds
        self.parallel = parallel
        self.reflection_fn = reflection_fn

    async def build_graph(self, goal: str, capabilities: list[str] | None = None) -> TaskGraph:
        """Decompose a goal and return a validated task graph."""
        graph = await self.planner.plan_async(goal, capabilities)
        errors = validate_task_graph(graph)
        if errors:
            raise ValueError("invalid task graph: " + "; ".join(errors))
        return graph

    async def execute(
        self,
        goal: Goal,
        graph: TaskGraph,
        *,
        workspace_id: str | None = None,
    ) -> None:
        """Plan (if needed) and run the goal's task graph into completion.

        Independent steps run concurrently (M6.1 parallel execution). Each step
        honours its ``retry`` policy and, when ``reflect`` is enabled, runs
        through the optional ``reflection_fn`` (M6.1 self-correction hook).
        """
        goal.context["task_graph"] = graph.to_dict()
        events: list[dict[str, Any]] = []
        goal.context["events"] = events  # live reference; filled as we go

        # Pre-flight approval gate: if any step needs approval and there is no
        # automated approver, raise before execution so the supervisor can pause
        # the goal (WAITING_APPROVAL) rather than fail it.
        if self.require_approval:
            for t in graph.tasks:
                if any(t.capability.startswith(p) for p in _APPROVAL_PREFIXES):
                    if self.approval_callback is None:
                        raise ApprovalRequiredError(
                            f"approval required for '{t.capability}'"
                        )
                    ok = bool(
                        await self.approval_callback(
                            goal_id=goal.goal_id,
                            capability=t.capability,
                            action=t.action,
                        )
                    )
                    if not ok:
                        raise ApprovalRequiredError(
                            f"approval rejected for '{t.capability}'"
                        )

        step_results: dict[str, dict[str, Any]] = {}
        self._last_outputs: dict[str, dict[str, Any]] = {}

        failed = await self._run_graph(
            goal, graph, events, step_results, workspace_id=workspace_id
        )

        # Keep the public Goal.steps records in sync with the executed results
        # so REST/WebSocket consumers (and the CLI) reflect real progress instead
        # of showing every step stuck in PENDING.
        self._sync_goal_steps(goal, graph, step_results)

        # Re-snapshot: dynamic replanning (via reflection) may have mutated the
        # graph, so persist the final shape, not just the initial plan.
        goal.context["task_graph"] = graph.to_dict()

        goal.context["workflow_result"] = {
            "status": "failed" if failed else "completed",
            "error": None if not failed else self._first_error(step_results),
            "step_results": step_results,
            "parallel": self.parallel,
        }

    def _sync_goal_steps(
        self,
        goal: Goal,
        graph: TaskGraph,
        step_results: dict[str, dict[str, Any]],
    ) -> None:
        """Mirror ``step_results`` into the public ``goal.steps`` records.

        ``goal.steps`` (StepRecord list) is what the gateway serialises for the
        REST API and CLI. The scheduler writes into ``step_results`` keyed by
        task id; without this sync consumers see every step frozen at PENDING.
        ``goal.steps`` is built in task order, so record[i] matches graph.tasks[i].
        """
        for record in goal.steps:
            task = next(
                (t for t in graph.tasks if t.id == record.skill or t.capability == record.skill),
                None,
            )
            if task is None:
                continue
            res = step_results.get(task.id)
            if res is None:
                continue
            record.status = (
                StepOutcome.SUCCESS if res.get("status") == "success" else StepOutcome.FAILED
            )
            record.error = res.get("error")
            record.result = res.get("outputs")
            record.attempts = max(record.attempts, int(res.get("attempts", 1) or 1))
            record.finished_at = record.finished_at or time.monotonic()

    async def _run_graph(
        self,
        goal: Goal,
        graph: TaskGraph,
        events: list[dict[str, Any]],
        step_results: dict[str, dict[str, Any]],
        *,
        workspace_id: str | None,
    ) -> bool:
        """Topological scheduler with parallel ready-sets, retry, and reflection.

        Returns ``True`` if the graph failed (any terminal step errored).
        """
        completed: set[str] = set()
        failed: set[str] = set()

        def ready() -> list[Task]:
            out = []
            for t in graph.tasks:
                if t.id in completed or t.id in failed:
                    continue
                if all(d in completed for d in t.depends_on):
                    out.append(t)
            return out

        while len(completed) + len(failed) < len(graph.tasks):
            batch = ready()
            if not batch:
                # No progress possible: a dependency is stuck (transitively failed).
                for t in graph.tasks:
                    if t.id not in completed and t.id not in failed:
                        failed.add(t.id)
                        events.append(self._ev("failed", t.id, "dependency failed"))
                break

            coros = [
                self._run_task(goal, t, events, workspace_id=workspace_id)
                for t in batch
            ]
            if self.parallel:
                results = await asyncio.gather(*coros, return_exceptions=True)
            else:
                results = [await c for c in coros]

            for task, res in zip(batch, results, strict=True):
                if isinstance(res, BaseException):
                    failed.add(task.id)
                    step_results[task.id] = {
                        "capability": task.capability,
                        "status": "failed",
                        "error": str(res),
                    }
                    events.append(self._ev("failed", task.id, str(res)))
                elif res.get("status") == "failed":
                    failed.add(task.id)
                    step_results[task.id] = res
                    events.append(self._ev("failed", task.id, res.get("error")))
                else:
                    completed.add(task.id)
                    step_results[task.id] = res
                    events.append(self._ev("completed", task.id, res))
                    # Reflection hook: allow self-correction / dynamic replanning.
                    if task.reflect and self.reflection_fn is not None:
                        try:
                            await self._maybe_await(
                                self.reflection_fn(task, res, graph)
                            )
                        except Exception:  # reflection must never break execution
                            logger.exception("reflection hook raised for %s", task.id)

        return bool(failed)

    async def _run_task(
        self,
        goal: Goal,
        task: Task,
        events: list[dict[str, Any]],
        *,
        workspace_id: str | None,
    ) -> dict[str, Any]:
        """Execute one task with its retry policy, returning its output dict."""
        retry = task.retry or {}
        max_retries = int(retry.get("max_retries", 0))
        backoff = float(retry.get("backoff_seconds", 0.0))
        last_error: str | None = None

        for attempt in range(max_retries + 1):
            if attempt:
                if backoff:
                    await asyncio.sleep(backoff)
                events.append(self._ev("retry", task.id, f"attempt {attempt + 1}"))
            events.append(self._ev("started", task.id, {"attempt": attempt + 1}))
            try:
                return await self._run_step(
                    task, workspace_id=workspace_id, goal_id=goal.goal_id
                )
            except Exception as exc:
                last_error = str(exc)
                if attempt >= max_retries:
                    raise

        # Should be unreachable; guarded for type-checkers.
        raise RuntimeError(last_error or "task failed")

    # ------------------------------------------------------------------ internals

    @staticmethod
    async def _maybe_await(value: Any) -> Any:
        if hasattr(value, "__await__"):
            return await value
        return value

    @staticmethod
    def _first_error(step_results: dict[str, dict[str, Any]]) -> str | None:
        for res in step_results.values():
            if res.get("status") == "failed":
                return res.get("error")
        return None

    def _ev(self, phase: str, step_id: str, data: Any) -> dict[str, Any]:
        return {"phase": phase, "step_id": step_id, "type": phase, "data": data}

    async def _run_step(
        self, task: Task, *, workspace_id: str | None, goal_id: str
    ) -> dict[str, Any]:
        capability = task.capability
        action = task.action
        inputs = dict(task.inputs)

        resolution = self.platform.resolve(capability)
        if not resolution.available or resolution.provider_id is None:
            raise RuntimeError(f"no available provider for capability '{capability}'")

        # Approval gate for sensitive capabilities (in-flight; pre-flight also
        # runs in execute()).
        if self.require_approval and any(
            capability.startswith(p) for p in _APPROVAL_PREFIXES
        ):
            if self.approval_callback is None:
                raise ApprovalRequiredError(f"approval required for '{capability}'")
            ok = bool(
                await self.approval_callback(
                    goal_id=goal_id, capability=capability, action=action
                )
            )
            if not ok:
                raise ApprovalRequiredError(f"approval rejected for '{capability}'")

        # Resolve template-style references like "{{browser}}" to prior outputs.
        inputs = self._resolve_refs(inputs, getattr(self, "_last_outputs", {}))

        result = await self.platform.execute_skill(
            resolution.provider_id,
            inputs={**inputs, "action": action},
            workspace_id=workspace_id,
            metadata={"goal_id": goal_id, "capability": capability},
        )
        status = getattr(result, "status", None)
        output = {
            "capability": capability,
            "skill": resolution.provider_id,
            "status": getattr(status, "value", status),
            "outputs": getattr(result, "outputs", {}),
            "error": getattr(result, "error", None),
        }
        self._last_outputs[task.id] = output
        if not getattr(result, "ok", False):
            raise RuntimeError(output["error"] or "skill failed")
        return output

    @staticmethod
    def _resolve_refs(inputs: dict[str, Any], outputs: dict[str, Any]) -> dict[str, Any]:
        def fill(value: Any) -> Any:
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                ref = value[2:-2].strip()
                return outputs.get(ref, {}).get("outputs", {})
            return value

        return {k: fill(v) for k, v in inputs.items()}


__all__ = ["NativeGoalRunner"]
