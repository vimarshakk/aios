"""AIOS Telemetry — OpenTelemetry tracing, metrics, structured logging, and health diagnostics."""

from __future__ import annotations

from aios.telemetry.health import HealthChecker, HealthStatus, check_health
from aios.telemetry.logging import get_logger, setup_logging
from aios.telemetry.metrics import MetricPoint, MetricsCollector
from aios.telemetry.tracing import (
    SpanKind,
    get_tracer,
    trace_operation,
)

API_VERSION = "1.0"

__all__ = [
    "HealthChecker",
    "HealthStatus",
    "MetricPoint",
    "MetricsCollector",
    "SpanKind",
    "check_health",
    "get_logger",
    "get_tracer",
    "setup_logging",
    "trace_operation",
]
