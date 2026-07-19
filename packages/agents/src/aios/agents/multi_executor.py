"""Multi-agent executor — parallel subtask execution with dependency resolution."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aios.agents.task import Subtask, resolve_execution_order

if TYPE_CHECKING:
    from aios.agents.pool import AgentPool


@dataclass
class SubtaskResult:
    """Result of executing a single subtask."""

    subtask_id: str
    agent_name: str
    response: str
    success: bool
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class MultiAgentExecutor:
    """Executes subtasks across agents with dependency-aware parallelism.

    Subtasks with no dependencies run concurrently. Subtasks that depend
    on others wait for their dependencies to complete before executing.
    """

    def __init__(self, pool: AgentPool) -> None:
        self._pool = pool
        self._results: dict[str, SubtaskResult] = {}

    async def execute(self, subtasks: list[Subtask]) -> list[SubtaskResult]:
        """Execute all subtasks with dependency resolution.

        Returns results in subtask order (not execution order).
        """
        self._results.clear()
        layers = resolve_execution_order(subtasks)

        for layer in layers:
            tasks = [
                self._execute_one(subtask) for subtask in layer
            ]
            await asyncio.gather(*tasks)

        # Return results in original subtask order
        return [
            self._results[s.id]
            for s in subtasks
            if s.id in self._results
        ]

    async def _execute_one(self, subtask: Subtask) -> SubtaskResult:
        """Execute a single subtask on the best available agent."""
        start = time.monotonic()

        entry = self._pool.select(subtask.required_capabilities)
        if not entry:
            result = SubtaskResult(
                subtask_id=subtask.id,
                agent_name="",
                response="",
                success=False,
                error=f"No agent available for capabilities: {subtask.required_capabilities}",
                duration_ms=(time.monotonic() - start) * 1000,
            )
            self._results[subtask.id] = result
            return result

        try:
            response = await entry.agent.run(subtask.query)
            elapsed = (time.monotonic() - start) * 1000
            result = SubtaskResult(
                subtask_id=subtask.id,
                agent_name=entry.name,
                response=response,
                success=True,
                duration_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            result = SubtaskResult(
                subtask_id=subtask.id,
                agent_name=entry.name,
                response="",
                success=False,
                error=str(exc),
                duration_ms=elapsed,
            )

        self._results[subtask.id] = result
        return result

    def get_result(self, subtask_id: str) -> SubtaskResult | None:
        """Get result by subtask ID."""
        return self._results.get(subtask_id)

    def clear(self) -> None:
        """Clear all stored results."""
        self._results.clear()
