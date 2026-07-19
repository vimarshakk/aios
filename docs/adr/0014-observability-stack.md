# ADR-0014: Observability Stack

**Date:** 2025-07-17
**Status:** Accepted
**Deciders:** Core team

## Context

M1 had basic logging. M3.3 introduced a comprehensive observability stack: structured tracing, metrics collection, structured logging, and health checking. These are in `packages/telemetry/` and provide first-class observability primitives.

## Decision

Four observability pillars:

- **Tracing:** `Tracer` with span creation, context propagation, attributes, events, status codes. Spans are stack-based (parent tracking). `traced` decorator for automatic span creation.
- **Metrics:** `MetricsCollector` with counters, gauges, histograms. Tags for dimensional data. `snapshot()` returns `list[MetricPoint]` (not dict). `get_counter(name, tags)` and `get_gauge(name, tags)` for reading values.
- **Logging:** `StructuredLogger` with key-value context, log levels, span context propagation. `bind(**ctx)` for adding context to all logs.
- **Health:** `HealthChecker` with named check registration, timeout per check, parallel execution. Returns `HealthStatus` (HEALTHY/UNHEALTHY/DEGRADED) with individual check results.

## Consequences

- `get_tracer()` and `get_logger()` are module-level convenience functions
- `setup_logging(level, format, handlers)` configures global logging
- `check_health(checks, timeout)` runs all health checks with a deadline
- Tracing uses `SpanKind` (UNSPECIFIED, SERVER, CLIENT, PRODUCER, CONSUMER)
- Metrics snapshot uses `key.split("|", 1)[0]` for metric name extraction (fixed bug: was `rsplit`)
- Health checks are async functions returning `HealthCheckResult` with `healthy`, `latency_ms`, `message`

## Key Bug Fixed

Metrics `snapshot()` initially used `key.rsplit("|", 1)[0]` which failed for tags with multiple `|` separators. Fixed to `key.split("|", 1)[0]` which correctly extracts the metric name.

## Alternatives Considered

1. **OpenTelemetry SDK:** More standard but adds dependency; we can adopt later
2. **Prometheus client:** Good for metrics but not tracing/logging
3. **Structlog:** Good library but we rolled our own for zero dependencies

## References

- `packages/telemetry/src/aios/telemetry/tracing.py`
- `packages/telemetry/src/aios/telemetry/metrics.py`
- `packages/telemetry/src/aios/telemetry/logging.py`
- `packages/telemetry/src/aios/telemetry/health.py`
- `tests/test_telemetry.py`
