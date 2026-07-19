"""Tests for AIOS Telemetry — M3.3 Observability."""

from __future__ import annotations

import pytest

from aios.telemetry.health import (
    CheckResult,
    HealthChecker,
    HealthStatus,
    check_health,
    get_health_checker,
    reset_health_checker,
)
from aios.telemetry.logging import (
    get_correlation_id,
    get_logger,
    get_subsystem,
    set_correlation_id,
    set_subsystem,
    setup_logging,
)
from aios.telemetry.metrics import (
    MetricsCollector,
    MetricType,
    get_metrics_collector,
    reset_metrics_collector,
)
from aios.telemetry.tracing import (
    SpanKind,
    get_tracer,
    init_tracing,
    reset_tracing,
    trace_operation,
    trace_sync,
)

# ─────────────────────────────────────────────
# Tracing
# ─────────────────────────────────────────────


class TestTracing:
    def test_init_tracing(self):
        provider = init_tracing("test-service", console_export=True)
        assert provider is not None

    def test_init_idempotent(self):
        p1 = init_tracing("test", console_export=True)
        p2 = init_tracing("test", console_export=True)
        assert p1 is p2

    def test_get_tracer(self):
        init_tracing("test-tracer", console_export=True)
        tracer = get_tracer("test")
        assert tracer is not None

    def test_reset_tracing(self):
        init_tracing("test-reset", console_export=True)
        reset_tracing()
        provider = init_tracing("test-reset-2", console_export=True)
        assert provider is not None

    @pytest.mark.asyncio
    async def test_trace_operation_decorator(self):
        init_tracing("test-decorator", console_export=True)

        @trace_operation("test.op")
        async def my_func(x: int) -> int:
            return x * 2

        result = await my_func(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_trace_operation_error(self):
        init_tracing("test-decorator-err", console_export=True)

        @trace_operation("test.fail")
        async def failing() -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await failing()

    def test_trace_sync_decorator(self):
        init_tracing("test-sync", console_export=True)

        @trace_sync("test.sync.op", kind=SpanKind.INTERNAL)
        def sync_func(x: int) -> int:
            return x + 1

        result = sync_func(41)
        assert result == 42


# ─────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────


class TestMetrics:
    def test_increment_counter(self):
        mc = MetricsCollector()
        mc.increment("requests")
        mc.increment("requests")
        assert mc.get_counter("requests") == 2.0

    def test_increment_with_tags(self):
        mc = MetricsCollector()
        mc.increment("http.total", tags={"method": "GET"})
        mc.increment("http.total", tags={"method": "POST"})
        assert mc.get_counter("http.total", tags={"method": "GET"}) == 1.0
        assert mc.get_counter("http.total", tags={"method": "POST"}) == 1.0

    def test_gauge(self):
        mc = MetricsCollector()
        mc.gauge("queue.depth", 42)
        assert mc.get_gauge("queue.depth") == 42
        mc.gauge("queue.depth", 10)
        assert mc.get_gauge("queue.depth") == 10

    def test_histogram(self):
        mc = MetricsCollector()
        mc.histogram("latency.ms", 100)
        mc.histogram("latency.ms", 200)
        mc.histogram("latency.ms", 150)
        snapshot = mc.snapshot()
        latency = [p for p in snapshot if p.name == "latency.ms"]
        assert len(latency) == 1
        assert latency[0].value == 450.0  # total
        assert latency[0].tags["count"] == "3"

    def test_snapshot(self):
        mc = MetricsCollector()
        mc.increment("a")
        mc.gauge("b", 5)
        mc.histogram("c", 1.5)
        points = mc.snapshot()
        assert len(points) == 3
        names = {p.name for p in points}
        assert names == {"a", "b", "c"}

    def test_clear(self):
        mc = MetricsCollector()
        mc.increment("x")
        mc.gauge("y", 1)
        mc.clear()
        assert mc.get_counter("x") == 0.0
        assert mc.get_gauge("y") is None

    def test_uptime(self):
        mc = MetricsCollector()
        assert mc.uptime >= 0

    def test_singleton(self):
        mc1 = get_metrics_collector()
        mc2 = get_metrics_collector()
        assert mc1 is mc2

    def test_reset_singleton(self):
        mc1 = get_metrics_collector()
        reset_metrics_collector()
        mc2 = get_metrics_collector()
        assert mc1 is not mc2

    def test_snapshot_types(self):
        mc = MetricsCollector()
        mc.increment("counter")
        mc.gauge("gauge", 1)
        mc.histogram("histogram", 1)
        points = mc.snapshot()
        types = {p.metric_type for p in points}
        assert MetricType.COUNTER in types
        assert MetricType.GAUGE in types
        assert MetricType.HISTOGRAM in types


# ─────────────────────────────────────────────
# Structured Logging
# ─────────────────────────────────────────────


class TestLogging:
    def test_setup_logging(self):
        setup_logging(level="DEBUG", json_output=False)

    def test_setup_json_logging(self):
        setup_logging(level="INFO", json_output=True)

    def test_get_logger(self):
        setup_logging(level="INFO", json_output=True)
        logger = get_logger("test")
        assert logger is not None
        logger.info("test_event", key="value")

    def test_correlation_id(self):
        cid = set_correlation_id("abc-123")
        assert cid == "abc-123"
        assert get_correlation_id() == "abc-123"

    def test_correlation_id_auto_generate(self):
        cid = set_correlation_id()
        assert len(cid) == 12

    def test_subsystem(self):
        set_subsystem("gateway")
        assert get_subsystem() == "gateway"
        set_subsystem("orchestrator")
        assert get_subsystem() == "orchestrator"


# ─────────────────────────────────────────────
# Health Checks
# ─────────────────────────────────────────────


class TestHealth:
    def test_health_checker_register(self):
        checker = HealthChecker()

        async def ok_check() -> CheckResult:
            return CheckResult(name="db", status=HealthStatus.HEALTHY)

        checker.register("db", ok_check)
        assert "db" in checker._checks

    def test_health_checker_unregister(self):
        checker = HealthChecker()

        async def ok_check() -> CheckResult:
            return CheckResult(name="db", status=HealthStatus.HEALTHY)

        checker.register("db", ok_check)
        checker.unregister("db")
        assert "db" not in checker._checks

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self):
        checker = HealthChecker()

        async def healthy() -> CheckResult:
            return CheckResult(name="ok", status=HealthStatus.HEALTHY)

        checker.register("ok", healthy)
        result = await checker.check()
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_degraded(self):
        checker = HealthChecker()

        async def degraded() -> CheckResult:
            return CheckResult(name="slow", status=HealthStatus.DEGRADED, message="slow")

        checker.register("slow", degraded)
        result = await checker.check()
        assert result["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        checker = HealthChecker()

        async def healthy() -> CheckResult:
            return CheckResult(name="ok", status=HealthStatus.HEALTHY)

        async def broken() -> CheckResult:
            return CheckResult(name="broken", status=HealthStatus.UNHEALTHY)

        checker.register("ok", healthy)
        checker.register("broken", broken)
        result = await checker.check()
        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_exception(self):
        checker = HealthChecker()

        async def crashing() -> CheckResult:
            raise RuntimeError("crash")

        checker.register("crasher", crashing)
        result = await checker.check()
        assert result["status"] == "unhealthy"
        assert "crash" in result["checks"]["crasher"]["message"]

    @pytest.mark.asyncio
    async def test_liveness(self):
        checker = HealthChecker()
        result = await checker.liveness()
        assert result["status"] == "alive"
        assert "uptime_seconds" in result

    @pytest.mark.asyncio
    async def test_readiness_healthy(self):
        checker = HealthChecker()

        async def ok() -> CheckResult:
            return CheckResult(name="svc", status=HealthStatus.HEALTHY)

        checker.register("svc", ok)
        result = await checker.readiness()
        assert result["ready"] is True

    @pytest.mark.asyncio
    async def test_readiness_unhealthy(self):
        checker = HealthChecker()

        async def bad() -> CheckResult:
            return CheckResult(name="svc", status=HealthStatus.UNHEALTHY)

        checker.register("svc", bad)
        result = await checker.readiness()
        assert result["ready"] is False

    @pytest.mark.asyncio
    async def test_last_results_caching(self):
        checker = HealthChecker()

        async def ok() -> CheckResult:
            return CheckResult(name="x", status=HealthStatus.HEALTHY)

        checker.register("x", ok)
        await checker.check()
        assert "x" in checker.last_results

    def test_global_health_checker(self):
        reset_health_checker()
        hc1 = get_health_checker()
        hc2 = get_health_checker()
        assert hc1 is hc2
        reset_health_checker()

    @pytest.mark.asyncio
    async def test_check_health_convenience(self):
        reset_health_checker()
        result = await check_health()
        assert "status" in result
        reset_health_checker()

    @pytest.mark.asyncio
    async def test_health_check_metadata(self):
        checker = HealthChecker()

        async def ok() -> CheckResult:
            return CheckResult(name="s", status=HealthStatus.HEALTHY)

        checker.register("s", ok)
        result = await checker.check()
        assert result["metadata"]["total_checks"] == 1
        assert "uptime_seconds" in result["metadata"]
