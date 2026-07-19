"""AIOS Telemetry Service — metrics, tracing, and observability."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("aios.telemetry")


class TelemetryService:
    """Lightweight telemetry collector for agent and system metrics.

    Tracks request counts, latencies, error rates, and custom events.
    """

    def __init__(self) -> None:
        self._metrics: dict[str, Any] = {}
        self._counters: dict[str, int] = {}
        self._timers: dict[str, float] = {}
        self._ready = False

    async def initialize(self) -> None:
        """Initialize telemetry backends."""
        self._ready = True
        logger.info("Telemetry service initialized")

    def record_counter(self, name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        self._counters[name] = self._counters.get(name, 0) + value

    def record_timer(self, name: str, duration: float) -> None:
        """Record a timer metric."""
        self._timers[name] = duration

    def record_event(self, name: str, data: dict[str, Any] | None = None) -> None:
        """Record an arbitrary event."""
        self._metrics[name] = {
            "timestamp": time.time(),
            "data": data or {},
        }

    def get_metrics(self) -> dict[str, Any]:
        """Return all collected metrics."""
        return {
            "counters": dict(self._counters),
            "timers": dict(self._timers),
            "events": dict(self._metrics),
        }

    async def flush(self) -> None:
        """Flush metrics to backend (placeholder)."""
        logger.debug("Flushing %d counters, %d timers, %d events",
                      len(self._counters), len(self._timers), len(self._metrics))

    async def close(self) -> None:
        """Shut down the telemetry service."""
        await self.flush()
        self._ready = False
        logger.info("Telemetry service closed")


_service: TelemetryService | None = None


def get_telemetry_service() -> TelemetryService:
    """Get the global telemetry service singleton."""
    global _service
    if _service is None:
        _service = TelemetryService()
    return _service
