"""Metrics collector — counters, gauges, and histograms for AIOS subsystems.

Provides an in-memory metrics store with optional OpenTelemetry export.
All metrics are thread-safe.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum


class MetricType(StrEnum):
    """Metric aggregation types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass(frozen=True, slots=True)
class MetricPoint:
    """A single metric data point.

    Attributes:
        name: Metric name (e.g. "llm.tokens.total").
        value: Current numeric value.
        metric_type: Counter, gauge, or histogram.
        tags: Key-value tags for dimensionality.
        timestamp: Unix timestamp of the measurement.
    """

    name: str
    value: float
    metric_type: MetricType
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class _HistogramBucket:
    """Internal histogram state."""

    counts: dict[float, int] = field(default_factory=lambda: defaultdict(int))
    total: float = 0.0
    count: int = 0
    min_val: float = float("inf")
    max_val: float = float("-inf")


class MetricsCollector:
    """Thread-safe in-memory metrics collector.

    Supports counters (monotonically increasing), gauges (current value),
    and histograms (distribution of values).

    Usage::

        mc = MetricsCollector()
        mc.increment("requests.total", tags={"method": "POST"})
        mc.gauge("queue.depth", 42)
        mc.histogram("latency.ms", 120.5)
        points = mc.snapshot()
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, _HistogramBucket] = defaultdict(_HistogramBucket)
        self._tag_index: dict[str, dict[str, str]] = {}
        self._created_at = time.time()

    def increment(
        self, name: str, value: float = 1.0, *, tags: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter metric.

        Args:
            name: Metric name.
            value: Amount to increment by (must be >= 0).
            tags: Optional dimension tags.
        """
        key = self._key(name, tags)
        with self._lock:
            self._counters[key] += value
            if tags:
                self._tag_index[key] = tags

    def gauge(self, name: str, value: float, *, tags: dict[str, str] | None = None) -> None:
        """Set a gauge metric to a specific value.

        Args:
            name: Metric name.
            value: Current value.
            tags: Optional dimension tags.
        """
        key = self._key(name, tags)
        with self._lock:
            self._gauges[key] = value
            if tags:
                self._tag_index[key] = tags

    def histogram(
        self, name: str, value: float, *, tags: dict[str, str] | None = None,
    ) -> None:
        """Record a value in a histogram.

        Args:
            name: Metric name.
            value: Observed value.
            tags: Optional dimension tags.
        """
        key = self._key(name, tags)
        with self._lock:
            bucket = self._histograms[key]
            bucket.total += value
            bucket.count += 1
            bucket.min_val = min(bucket.min_val, value)
            bucket.max_val = max(bucket.max_val, value)
            bucket.counts[round(value, 2)] += 1
            if tags:
                self._tag_index[key] = tags

    def snapshot(self) -> list[MetricPoint]:
        """Return a snapshot of all current metrics.

        Returns:
            List of MetricPoint objects representing current state.
        """
        points: list[MetricPoint] = []
        now = time.time()

        with self._lock:
            for key, value in self._counters.items():
                tags = self._tag_index.get(key, {})
                name = key.split("|", 1)[0]
                points.append(
                    MetricPoint(
                        name=name,
                        value=value,
                        metric_type=MetricType.COUNTER,
                        tags=tags,
                        timestamp=now,
                    )
                )

            for key, value in self._gauges.items():
                tags = self._tag_index.get(key, {})
                name = key.split("|", 1)[0]
                points.append(
                    MetricPoint(
                        name=name,
                        value=value,
                        metric_type=MetricType.GAUGE,
                        tags=tags,
                        timestamp=now,
                    )
                )

            for key, bucket in self._histograms.items():
                tags = self._tag_index.get(key, {})
                name = key.split("|", 1)[0]
                points.append(
                    MetricPoint(
                        name=name,
                        value=bucket.total,
                        metric_type=MetricType.HISTOGRAM,
                        tags={
                            **tags,
                            "count": str(bucket.count),
                            "min": str(bucket.min_val) if bucket.count > 0 else "0",
                            "max": str(bucket.max_val) if bucket.count > 0 else "0",
                        },
                        timestamp=now,
                    )
                )

        return points

    def get_counter(self, name: str, *, tags: dict[str, str] | None = None) -> float:
        """Get the current value of a counter."""
        key = self._key(name, tags)
        with self._lock:
            return self._counters.get(key, 0.0)

    def get_gauge(self, name: str, *, tags: dict[str, str] | None = None) -> float | None:
        """Get the current value of a gauge."""
        key = self._key(name, tags)
        with self._lock:
            return self._gauges.get(key)

    def clear(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._tag_index.clear()

    @property
    def uptime(self) -> float:
        """Seconds since the collector was created."""
        return time.time() - self._created_at

    @staticmethod
    def _key(name: str, tags: dict[str, str] | None) -> str:
        """Build a unique key from name and tags."""
        if not tags:
            return name
        tag_str = "|".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}|{tag_str}"


_collector: MetricsCollector | None = None
_collector_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """Get the global MetricsCollector singleton."""
    global _collector
    with _collector_lock:
        if _collector is None:
            _collector = MetricsCollector()
        return _collector


def reset_metrics_collector() -> None:
    """Reset the global MetricsCollector (for testing)."""
    global _collector
    with _collector_lock:
        _collector = None


__all__ = [
    "MetricPoint",
    "MetricType",
    "MetricsCollector",
    "get_metrics_collector",
    "reset_metrics_collector",
]
