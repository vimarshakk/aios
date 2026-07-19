"""Telemetry integration — traces, metrics, and health for distributed execution.

Provides decorators and helpers that wire the distributed execution
modules into the aios-telemetry observability stack.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from aios.telemetry.health import CheckResult, HealthChecker, HealthStatus
from aios.telemetry.tracing import SpanKind, trace_operation

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from aios.telemetry.metrics import MetricsCollector


@dataclass
class QueueMetrics:
    """Metrics collector for queue operations.

    Tracks enqueue/dequeue rates, latency, depth, and error counts.
    """

    collector: MetricsCollector
    _prefix: str = "aios.queue"

    def record_enqueue(self, queue: str, priority: int = 5) -> None:
        tags = {"queue": queue, "priority": str(priority)}
        self.collector.increment(f"{self._prefix}.enqueued", tags=tags)

    def record_dequeue(self, queue: str) -> None:
        self.collector.increment(f"{self._prefix}.dequeued", tags={"queue": queue})

    def record_ack(self, queue: str) -> None:
        self.collector.increment(f"{self._prefix}.acked", tags={"queue": queue})

    def record_nack(self, queue: str) -> None:
        self.collector.increment(f"{self._prefix}.nacked", tags={"queue": queue})

    def record_latency(self, queue: str, operation: str, ms: float) -> None:
        self.collector.histogram(
            f"{self._prefix}.latency",
            ms,
            tags={"queue": queue, "operation": operation},
        )

    def record_depth(self, queue: str, depth: int) -> None:
        self.collector.gauge(f"{self._prefix}.depth", float(depth), tags={"queue": queue})

    def record_error(self, queue: str, error_type: str) -> None:
        self.collector.increment(
            f"{self._prefix}.errors",
            tags={"queue": queue, "error_type": error_type},
        )


@dataclass
class WorkerMetrics:
    """Metrics collector for worker operations."""

    collector: MetricsCollector
    _prefix: str = "aios.worker"

    def record_task_completed(
        self, worker_id: str, task_type: str, duration_ms: float,
    ) -> None:
        tags = {"worker": worker_id, "type": task_type}
        self.collector.increment(f"{self._prefix}.completed", tags=tags)
        self.collector.histogram(
            f"{self._prefix}.duration", duration_ms, tags=tags,
        )

    def record_task_failed(self, worker_id: str, task_type: str, error_type: str) -> None:
        self.collector.increment(
            f"{self._prefix}.failed",
            tags={"worker": worker_id, "type": task_type, "error": error_type},
        )

    def record_task_retried(self, worker_id: str, attempt: int) -> None:
        tags = {"worker": worker_id, "attempt": str(attempt)}
        self.collector.increment(f"{self._prefix}.retried", tags=tags)

    def record_dlq(self, worker_id: str, task_type: str) -> None:
        tags = {"worker": worker_id, "type": task_type}
        self.collector.increment(f"{self._prefix}.dead_lettered", tags=tags)

    def record_active_workers(self, count: int) -> None:
        self.collector.gauge(f"{self._prefix}.active", float(count))


@dataclass
class SchedulerMetrics:
    """Metrics collector for scheduler operations."""

    collector: MetricsCollector
    _prefix: str = "aios.scheduler"

    def record_job_fired(self, job_name: str) -> None:
        self.collector.increment(f"{self._prefix}.fired", tags={"job": job_name})

    def record_job_error(self, job_name: str, error_type: str) -> None:
        tags = {"job": job_name, "error": error_type}
        self.collector.increment(f"{self._prefix}.errors", tags=tags)

    def record_scheduled_jobs(self, count: int) -> None:
        self.collector.gauge(f"{self._prefix}.jobs", float(count))


@dataclass
class LockMetrics:
    """Metrics collector for distributed lock operations."""

    collector: MetricsCollector
    _prefix: str = "aios.lock"

    def record_acquire(self, name: str, *, success: bool) -> None:
        self.collector.increment(
            f"{self._prefix}.acquire",
            tags={"lock": name, "success": str(success).lower()},
        )

    def record_release(self, name: str) -> None:
        self.collector.increment(f"{self._prefix}.released", tags={"lock": name})

    def record_contention(self, name: str, wait_ms: float) -> None:
        self.collector.histogram(f"{self._prefix}.contention", wait_ms, tags={"lock": name})


def traced_task(task_type: str) -> Callable:
    """Decorator that traces a task handler execution.

    Creates an OpenTelemetry span around the handler call with
    task type, attempt, and duration attributes.

    Usage::

        @traced_task("llm.generate")
        async def handle_generate(msg: TaskMessage) -> Any:
            ...
    """

    def decorator(
        fn: Callable[..., Coroutine[Any, Any, Any]],
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        @trace_operation(f"task.{task_type}", kind=SpanKind.INTERNAL)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await fn(*args, **kwargs)
        return wrapper  # type: ignore[return-value]

    return decorator


def register_queue_health(
    health_checker: HealthChecker,
    queue_name: str,
    check_fn: Callable[[], Coroutine[Any, Any, bool]],
) -> None:
    """Register a queue health check with the global health checker.

    Args:
        health_checker: The HealthChecker instance.
        queue_name: Name of the queue for the check.
        check_fn: Async function that returns True if the queue is healthy.
    """

    async def queue_health_check() -> CheckResult:
        start = time.monotonic()
        try:
            healthy = await check_fn()
            latency = (time.monotonic() - start) * 1000
            return CheckResult(
                name=f"queue:{queue_name}",
                status=HealthStatus.HEALTHY if healthy else HealthStatus.DEGRADED,
                latency_ms=latency,
            )
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return CheckResult(
                name=f"queue:{queue_name}",
                status=HealthStatus.UNHEALTHY,
                message=str(exc),
                latency_ms=latency,
            )

    health_checker.register(f"queue:{queue_name}", queue_health_check)


def register_worker_health(
    health_checker: HealthChecker,
    worker_id: str,
    is_running_fn: Callable[[], bool],
) -> None:
    """Register a worker health check."""

    async def worker_health_check() -> CheckResult:
        running = is_running_fn()
        return CheckResult(
            name=f"worker:{worker_id}",
            status=HealthStatus.HEALTHY if running else HealthStatus.UNHEALTHY,
        )

    health_checker.register(f"worker:{worker_id}", worker_health_check)


__all__ = [
    "LockMetrics",
    "QueueMetrics",
    "SchedulerMetrics",
    "WorkerMetrics",
    "register_queue_health",
    "register_worker_health",
    "traced_task",
]
