"""Tests for aios.integrations — integration registry and lifecycle."""

from __future__ import annotations

import pytest

from aios.integrations.base import Integration
from aios.integrations.registry import IntegrationRegistry
from aios.integrations.types import (
    HealthCheckResult,
    IntegrationConfig,
    IntegrationResult,
    IntegrationStatus,
)


class FakeIntegration(Integration):
    """Minimal integration for testing."""

    def __init__(
        self,
        name: str = "fake",
        *,
        fail_connect: bool = False,
        fail_execute: bool = False,
        fail_health: bool = False,
    ) -> None:
        super().__init__(IntegrationConfig(name=name))
        self._fail_connect = fail_connect
        self._fail_execute = fail_execute
        self._fail_health = fail_health
        self.connect_called = False
        self.disconnect_called = False
        self.execute_calls: list[str] = []

    async def connect(self) -> None:
        self.connect_called = True
        if self._fail_connect:
            raise ConnectionError("Cannot connect")

    async def disconnect(self) -> None:
        self.disconnect_called = True

    async def health_check(self) -> HealthCheckResult:
        if self._fail_health:
            return HealthCheckResult(healthy=False, message="unhealthy")
        return HealthCheckResult(healthy=True, latency_ms=1.5)

    async def execute(self, action: str, **kwargs: object) -> IntegrationResult:
        self.execute_calls.append(action)
        if self._fail_execute:
            return IntegrationResult(ok=False, error="action failed")
        return IntegrationResult(ok=True, data={"action": action})


class UnnamedIntegration(Integration):
    """Integration with no name in config — tests class name fallback."""

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(healthy=True)

    async def execute(self, action: str, **kwargs: object) -> IntegrationResult:
        return IntegrationResult(ok=True)


# ── IntegrationConfig ──────────────────────────────────────────────────


class TestIntegrationConfig:
    def test_default_config(self) -> None:
        cfg = IntegrationConfig()
        assert cfg.name == ""
        assert cfg.api_key == ""
        assert cfg.base_url == ""
        assert cfg.timeout == 30.0
        assert cfg.max_retries == 3
        assert cfg.headers == {}
        assert cfg.metadata == {}

    def test_custom_config(self) -> None:
        cfg = IntegrationConfig(
            name="github",
            api_key="ghp_abc",
            base_url="https://api.github.com",
            timeout=10.0,
            max_retries=5,
            headers={"Accept": "application/json"},
            metadata={"env": "production"},
        )
        assert cfg.name == "github"
        assert cfg.api_key == "ghp_abc"
        assert cfg.base_url == "https://api.github.com"
        assert cfg.timeout == 10.0
        assert cfg.max_retries == 5
        assert cfg.metadata["env"] == "production"


# ── IntegrationStatus ─────────────────────────────────────────────────


class TestIntegrationStatus:
    def test_all_statuses(self) -> None:
        expected = [
            "discovered",
            "configured",
            "connecting",
            "connected",
            "error",
            "disabled",
            "disconnecting",
        ]
        for status_str in expected:
            status = IntegrationStatus(status_str)
            assert status.value == status_str


# ── IntegrationResult ──────────────────────────────────────────────────


class TestIntegrationResult:
    def test_ok_result(self) -> None:
        r = IntegrationResult(ok=True, data={"key": "value"})
        assert r.ok is True
        assert r.data == {"key": "value"}
        assert r.error is None

    def test_error_result(self) -> None:
        r = IntegrationResult(ok=False, error="bad request", status=IntegrationStatus.ERROR)
        assert r.ok is False
        assert r.error == "bad request"
        assert r.status == IntegrationStatus.ERROR


# ── HealthCheckResult ──────────────────────────────────────────────────


class TestHealthCheckResult:
    def test_healthy(self) -> None:
        h = HealthCheckResult(healthy=True, latency_ms=5.0, message="all good")
        assert h.healthy is True
        assert h.latency_ms == 5.0
        assert h.message == "all good"

    def test_unhealthy(self) -> None:
        h = HealthCheckResult(healthy=False, message="timeout")
        assert h.healthy is False


# ── Integration Base ───────────────────────────────────────────────────


class TestIntegrationBase:
    def test_initial_status(self) -> None:
        integ = FakeIntegration(name="test")
        assert integ.status == IntegrationStatus.DISCOVERED
        assert integ.is_connected is False
        assert integ.name == "test"

    def test_default_name(self) -> None:
        integ = UnnamedIntegration()
        assert integ.name == "UnnamedIntegration"

    @pytest.mark.asyncio
    async def test_initialize_success(self) -> None:
        integ = FakeIntegration(name="svc")
        result = await integ.initialize()
        assert result.ok is True
        assert result.status == IntegrationStatus.CONNECTED
        assert integ.is_connected is True
        assert integ.connect_called is True
        assert integ.uptime_seconds >= 0.0

    @pytest.mark.asyncio
    async def test_initialize_failure(self) -> None:
        integ = FakeIntegration(name="fail", fail_connect=True)
        result = await integ.initialize()
        assert result.ok is False
        assert result.status == IntegrationStatus.ERROR
        assert integ.status == IntegrationStatus.ERROR

    @pytest.mark.asyncio
    async def test_shutdown_success(self) -> None:
        integ = FakeIntegration(name="svc")
        await integ.initialize()
        result = await integ.shutdown()
        assert result.ok is True
        assert result.status == IntegrationStatus.DISABLED
        assert integ.is_connected is False
        assert integ.disconnect_called is True

    @pytest.mark.asyncio
    async def test_configure_while_connected_raises(self) -> None:
        integ = FakeIntegration(name="svc")
        await integ.initialize()
        with pytest.raises(RuntimeError, match="Cannot reconfigure while connected"):
            integ.configure(IntegrationConfig(name="new"))

    @pytest.mark.asyncio
    async def test_safe_execute_while_connected(self) -> None:
        integ = FakeIntegration(name="svc")
        await integ.initialize()
        result = await integ.safe_execute("list_items")
        assert result.ok is True
        assert result.data == {"action": "list_items"}

    @pytest.mark.asyncio
    async def test_safe_execute_not_connected(self) -> None:
        integ = FakeIntegration(name="svc")
        result = await integ.safe_execute("list_items")
        assert result.ok is False
        assert "not connected" in result.error

    def test_repr(self) -> None:
        integ = FakeIntegration(name="repr_test")
        r = repr(integ)
        assert "FakeIntegration" in r
        assert "repr_test" in r
        assert "discovered" in r


# ── IntegrationRegistry ────────────────────────────────────────────────


class TestIntegrationRegistry:
    def test_register_and_get(self) -> None:
        reg = IntegrationRegistry()
        integ = FakeIntegration(name="svc1")
        reg.register(integ)
        assert reg.get("svc1") is integ
        assert reg.has("svc1") is True
        assert reg.count == 1

    def test_register_duplicate_raises(self) -> None:
        reg = IntegrationRegistry()
        reg.register(FakeIntegration(name="dup"))
        with pytest.raises(ValueError, match="already registered"):
            reg.register(FakeIntegration(name="dup"))

    def test_unregister(self) -> None:
        reg = IntegrationRegistry()
        reg.register(FakeIntegration(name="svc"))
        removed = reg.unregister("svc")
        assert removed is not None
        assert reg.has("svc") is False
        assert reg.count == 0

    def test_unregister_nonexistent(self) -> None:
        reg = IntegrationRegistry()
        assert reg.unregister("nope") is None

    def test_names_and_all(self) -> None:
        reg = IntegrationRegistry()
        reg.register(FakeIntegration(name="a"))
        reg.register(FakeIntegration(name="b"))
        assert sorted(reg.names) == ["a", "b"]
        assert len(reg.all()) == 2

    def test_by_status(self) -> None:
        reg = IntegrationRegistry()
        a = FakeIntegration(name="a")
        b = FakeIntegration(name="b")
        reg.register(a)
        reg.register(b)
        assert len(reg.by_status(IntegrationStatus.DISCOVERED)) == 2
        assert len(reg.connected()) == 0

    @pytest.mark.asyncio
    async def test_connect_all(self) -> None:
        reg = IntegrationRegistry()
        reg.register(FakeIntegration(name="a"))
        reg.register(FakeIntegration(name="b"))
        results = await reg.connect_all()
        assert results == {"a": True, "b": True}
        assert len(reg.connected()) == 2

    @pytest.mark.asyncio
    async def test_connect_all_partial_failure(self) -> None:
        reg = IntegrationRegistry()
        reg.register(FakeIntegration(name="ok"))
        reg.register(FakeIntegration(name="fail", fail_connect=True))
        results = await reg.connect_all()
        assert results["ok"] is True
        assert results["fail"] is False
        assert len(reg.connected()) == 1
        assert len(reg.errored()) == 1

    @pytest.mark.asyncio
    async def test_disconnect_all(self) -> None:
        reg = IntegrationRegistry()
        reg.register(FakeIntegration(name="a"))
        await reg.connect_all()
        results = await reg.disconnect_all()
        assert results == {"a": True}
        assert len(reg.connected()) == 0

    def test_stats(self) -> None:
        reg = IntegrationRegistry()
        reg.register(FakeIntegration(name="a"))
        reg.register(FakeIntegration(name="b"))
        stats = reg.stats()
        assert stats.total == 2
        assert stats.connected == 0
        assert stats.errored == 0
        assert stats.disabled == 0

    def test_clear(self) -> None:
        reg = IntegrationRegistry()
        reg.register(FakeIntegration(name="a"))
        reg.register(FakeIntegration(name="b"))
        count = reg.clear()
        assert count == 2
        assert reg.count == 0

    def test_contains_and_len(self) -> None:
        reg = IntegrationRegistry()
        reg.register(FakeIntegration(name="x"))
        assert "x" in reg
        assert "y" not in reg
        assert len(reg) == 1

    def test_repr(self) -> None:
        reg = IntegrationRegistry()
        assert "0" in repr(reg)
