"""Health diagnostics — subsystem health checks and readiness probes.

Provides a HealthChecker that aggregates checks from all subsystems,
supports liveness and readiness probes, and returns structured health
reports suitable for Kubernetes or Docker health endpoints.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class HealthStatus(StrEnum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Result of a single health check.

    Attributes:
        name: Subsystem name.
        status: Health status.
        message: Human-readable message.
        latency_ms: How long the check took.
        details: Additional diagnostic data.
    """

    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


CheckFn = Callable[[], Coroutine[Any, Any, CheckResult]]


class HealthChecker:
    """Aggregated health checker for all AIOS subsystems.

    Usage::

        checker = HealthChecker()
        checker.register("database", check_db_health)
        checker.register("redis", check_redis_health)
        report = await checker.check()
    """

    def __init__(self) -> None:
        self._checks: dict[str, CheckFn] = {}
        self._last_results: dict[str, CheckResult] = {}
        self._started_at = time.time()

    def register(self, name: str, check_fn: CheckFn) -> None:
        """Register a health check function for a subsystem.

        Args:
            name: Subsystem name (e.g. "database", "redis", "gateway").
            check_fn: Async function that returns a CheckResult.
        """
        self._checks[name] = check_fn

    def unregister(self, name: str) -> None:
        """Remove a health check."""
        self._checks.pop(name, None)
        self._last_results.pop(name, None)

    async def check(self) -> dict[str, Any]:
        """Run all registered health checks and return a structured report.

        Args:


        Returns:
            A dict with overall status, per-subsystem results, and metadata.
        """
        results: list[CheckResult] = []
        start = time.monotonic()

        for name, check_fn in self._checks.items():
            check_start = time.monotonic()
            try:
                result = await check_fn()
            except Exception as exc:
                result = CheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {exc}",
                    latency_ms=(time.monotonic() - check_start) * 1000,
                )
            results.append(result)
            self._last_results[name] = result

        total_ms = (time.monotonic() - start) * 1000

        statuses = [r.status for r in results]
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.UNKNOWN

        return {
            "status": overall.value,
            "checks": {
                r.name: {
                    "status": r.status.value,
                    "message": r.message,
                    "latency_ms": round(r.latency_ms, 2),
                    "details": r.details,
                }
                for r in results
            },
            "metadata": {
                "total_checks": len(results),
                "total_latency_ms": round(total_ms, 2),
                "uptime_seconds": round(time.time() - self._started_at, 1),
                "registered_subsystems": list(self._checks.keys()),
            },
        }

    async def liveness(self) -> dict[str, Any]:
        """Liveness probe — returns OK if the process is running.

        This does NOT check subsystem health, only that the checker
        itself is responsive.
        """
        return {
            "status": "alive",
            "uptime_seconds": round(time.time() - self._started_at, 1),
        }

    async def readiness(self) -> dict[str, Any]:
        """Readiness probe — checks if all critical subsystems are healthy.

        Returns a readiness report suitable for Kubernetes readiness probes.
        """
        report = await self.check()
        is_ready = report["status"] in ("healthy", "degraded")
        return {
            "ready": is_ready,
            "status": report["status"],
            "subsystems": report["metadata"]["registered_subsystems"],
        }

    @property
    def last_results(self) -> dict[str, CheckResult]:
        """Most recent check results (cached)."""
        return dict(self._last_results)


_health_checker: HealthChecker | None = None
_health_lock = __import__("threading").Lock()


def get_health_checker() -> HealthChecker:
    """Get the global HealthChecker singleton."""
    global _health_checker
    with _health_lock:
        if _health_checker is None:
            _health_checker = HealthChecker()
        return _health_checker


def reset_health_checker() -> None:
    """Reset the global HealthChecker (for testing)."""
    global _health_checker
    with _health_lock:
        _health_checker = None


async def check_health() -> dict[str, Any]:
    """Convenience function to run a full health check."""
    return await get_health_checker().check()


__all__ = [
    "CheckResult",
    "HealthChecker",
    "HealthStatus",
    "check_health",
    "get_health_checker",
    "reset_health_checker",
]
