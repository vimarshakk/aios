"""Parallel step execution — run multiple steps concurrently."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


@dataclass
class ParallelGroup:
    """A group of step IDs that should execute concurrently.

    Attributes:
        group_id: Unique identifier for this parallel group.
        step_ids: Steps to run in parallel.
        fail_fast: If True, cancel remaining steps when any one fails.
        timeout_seconds: Max time for the entire group (None = unlimited).
    """

    group_id: str = ""
    step_ids: list[str] = field(default_factory=list)
    fail_fast: bool = True
    timeout_seconds: float | None = None


@dataclass
class ParallelResult:
    """Result of executing a parallel group.

    Attributes:
        group_id: The group that was executed.
        results: Mapping of step_id → result (or exception).
        succeeded: Step IDs that completed successfully.
        failed: Step IDs that failed.
        timed_out: True if the group hit its timeout.
    """

    group_id: str
    results: dict[str, Any] = field(default_factory=dict)
    succeeded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    timed_out: bool = False


async def execute_parallel(
    group: ParallelGroup,
    step_fn: Callable[[str], Awaitable[Any]],
    *,
    fail_fast: bool = True,
    timeout_seconds: float | None = None,
) -> ParallelResult:
    """Execute a group of steps concurrently.

    Args:
        group: The ParallelGroup defining which steps to run.
        step_fn: Async callable that takes a step_id and returns its result.
        fail_fast: Override group.fail_fast if provided.
        timeout_seconds: Override group.timeout_seconds if provided.

    Returns:
        ParallelResult with per-step outcomes.
    """
    _fail_fast = fail_fast if fail_fast is not None else group.fail_fast
    _timeout = timeout_seconds if timeout_seconds is not None else group.timeout_seconds

    result = ParallelResult(group_id=group.group_id)
    tasks: dict[str, asyncio.Task[Any]] = {}

    for sid in group.step_ids:
        task = asyncio.create_task(_safe_call(step_fn, sid))
        tasks[sid] = task

    done, pending = await asyncio.wait(tasks.values(), timeout=_timeout)
    if pending:
        result.timed_out = True
        for t in pending:
            t.cancel()
        # Allow cancelled tasks to settle so their state is finalised
        await asyncio.gather(*pending, return_exceptions=True)
        done = set(tasks.values())

    # Map results back to step IDs
    task_to_id = {id(t): sid for sid, t in tasks.items()}
    for t in done:
        sid = task_to_id[id(t)]
        if t.cancelled():
            result.failed.append(sid)
            result.results[sid] = asyncio.CancelledError()
        else:
            try:
                value = t.result()
                result.succeeded.append(sid)
                result.results[sid] = value
            except Exception as exc:
                result.failed.append(sid)
                result.results[sid] = exc
                if _fail_fast:
                    for remaining_t in tasks.values():
                        if not remaining_t.done():
                            remaining_t.cancel()
                    break

    return result


async def _safe_call(fn: Callable[[str], Awaitable[Any]], step_id: str) -> Any:
    """Wrap a callable to catch exceptions."""
    return await fn(step_id)
