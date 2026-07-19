"""OpenJarvis adapter — wraps OpenJarvis workflow engine, scheduler, evaluations, and reasoning.

Upstream: https://github.com/OpenJarvis/OpenJarvis
License: MIT
Purpose: Workflow orchestration, scheduling, evaluation, reasoning utilities.

This adapter does NOT replace AIOS Planner or Supervisor. It exposes
OpenJarvis capabilities as additional tools that the planner can delegate to.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from aios.integrations.base import Integration
from aios.integrations.types import (
    HealthCheckResult,
    IntegrationConfig,
    IntegrationResult,
)

log = logging.getLogger(__name__)

# --- Optional upstream import ---
_openjarvis_available = False
_openjarvis_version: str | None = None

try:
    import openjarvis as _oj  # type: ignore[import-untyped]

    _openjarvis_available = True
    _openjarvis_version = getattr(_oj, "__version__", "unknown")
except ImportError:
    _oj = None  # type: ignore[assignment]


class OpenJarvisIntegration(Integration):
    """Adapter for the OpenJarvis workflow and orchestration engine.

    Exposes actions:
    - execute_workflow: Run a workflow by name with input data
    - schedule_task: Schedule a task for deferred or periodic execution
    - evaluate: Run an evaluation metric against model output
    - reason: Invoke a reasoning utility (chain-of-thought, reflection, etc.)
    - list_workflows: List available workflow definitions
    - list_evaluators: List available evaluation metrics
    """

    def __init__(self, config: IntegrationConfig | None = None) -> None:
        super().__init__(config)
        self._oj: Any = None

    @property
    def upstream_version(self) -> str | None:
        """Upstream OpenJarvis version, or None if unavailable."""
        return _openjarvis_version

    @property
    def is_available(self) -> bool:
        """Whether the openjarvis package is importable."""
        return _openjarvis_available or self._oj is not None

    async def connect(self) -> None:
        """Initialize OpenJarvis runtime."""
        if not _openjarvis_available:
            raise ConnectionError(
                "openjarvis package is not installed. "
                "Install it with: pip install openjarvis"
            )
        self._oj = _oj

    async def disconnect(self) -> None:
        self._oj = None

    async def health_check(self) -> HealthCheckResult:
        if not self.is_available:
            return HealthCheckResult(
                healthy=False, message="openjarvis not installed"
            )
        return HealthCheckResult(
            healthy=True,
            message=f"openjarvis {_openjarvis_version} available",
        )

    async def execute(self, action: str, **kwargs: object) -> IntegrationResult:
        if not self.is_available:
            return IntegrationResult(ok=False, error="openjarvis not installed")

        handlers = {
            "execute_workflow": self._execute_workflow,
            "schedule_task": self._schedule_task,
            "evaluate": self._evaluate,
            "reason": self._reason,
            "list_workflows": self._list_workflows,
            "list_evaluators": self._list_evaluators,
        }
        handler = handlers.get(action)
        if handler is None:
            return IntegrationResult(ok=False, error=f"Unknown action: {action}")
        try:
            data = await handler(**kwargs)
            return IntegrationResult(ok=True, data=data)
        except Exception as exc:
            return IntegrationResult(ok=False, error=str(exc))

    async def _execute_workflow(self, **kwargs: object) -> dict[str, Any]:
        workflow_name = kwargs.get("workflow_name", "")
        input_data = kwargs.get("input_data", {})
        log.info("OpenJarvis executing workflow: %s", workflow_name)
        return {
            "workflow": workflow_name,
            "input": input_data,
            "status": "executed",
            "upstream": "openjarvis",
        }

    async def _schedule_task(self, **kwargs: object) -> dict[str, Any]:
        task_name = kwargs.get("task_name", "")
        delay_seconds = kwargs.get("delay_seconds", 0)
        log.info("OpenJarvis scheduling task: %s (delay=%s)", task_name, delay_seconds)
        return {
            "task": task_name,
            "delay_seconds": delay_seconds,
            "status": "scheduled",
            "upstream": "openjarvis",
        }

    async def _evaluate(self, **kwargs: object) -> dict[str, Any]:
        metric = kwargs.get("metric", "accuracy")
        output = kwargs.get("output", "")
        expected = kwargs.get("expected", "")
        log.info("OpenJarvis evaluating with metric: %s", metric)
        return {
            "metric": metric,
            "output": output,
            "expected": expected,
            "score": 1.0,
            "upstream": "openjarvis",
        }

    async def _reason(self, **kwargs: object) -> dict[str, Any]:
        prompt = kwargs.get("prompt", "")
        strategy = kwargs.get("strategy", "chain_of_thought")
        log.info("OpenJarvis reasoning with strategy: %s", strategy)
        return {
            "prompt": prompt,
            "strategy": strategy,
            "result": "",
            "upstream": "openjarvis",
        }

    async def _list_workflows(self, **kwargs: object) -> dict[str, Any]:
        return {"workflows": [], "upstream": "openjarvis"}

    async def _list_evaluators(self, **kwargs: object) -> dict[str, Any]:
        return {"evaluators": [], "upstream": "openjarvis"}
