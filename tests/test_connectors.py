"""Tests for aios.integrations connector layer (ADR-0019 bridge)."""

from __future__ import annotations

import pytest

from aios.agents.permissions import Permission, PermissionSet
from aios.integrations.base import Integration
from aios.integrations.connector import (
    ConnectorBinding,
    ConnectorRegistry,
)
from aios.integrations.connectors import (
    DockerConnector,
    FilesystemConnector,
    GitHubConnector,
    GmailConnector,
    SlackConnector,
)
from aios.integrations.types import IntegrationResult, IntegrationStatus


class _FakeIntegration(Integration):
    def __init__(self, name: str = "fake") -> None:
        from aios.integrations.types import IntegrationConfig

        super().__init__(IntegrationConfig(name=name))
        self.calls: list[tuple[str, dict]] = []
        self._status = IntegrationStatus.CONNECTED
        self._connected_at = 0.0

    async def connect(self) -> None:
        self._status = IntegrationStatus.CONNECTED

    async def disconnect(self) -> None:
        self._status = IntegrationStatus.DISABLED

    async def health_check(self):
        from aios.integrations.types import HealthCheckResult

        return HealthCheckResult(healthy=True)

    async def execute(self, action: str, **kwargs: object) -> IntegrationResult:
        self.calls.append((action, kwargs))
        return IntegrationResult(ok=True, data={"action": action, "kwargs": kwargs})


class TestConnectorBinding:
    def test_fields(self) -> None:
        b = ConnectorBinding(
            capability="git.push", action="push",
            required_permissions=(Permission.PROCESS_EXEC,),
        )
        assert b.capability == "git.push"
        assert b.action == "push"
        assert b.required_permissions == (Permission.PROCESS_EXEC,)


class TestGitHubConnector:
    def test_capabilities(self) -> None:
        conn = GitHubConnector(_FakeIntegration("gh"))
        assert "git.push" in conn.capabilities()
        assert conn.can_handle("git.push")
        assert not conn.can_handle("slack.send")

    def test_binding_for(self) -> None:
        conn = GitHubConnector(_FakeIntegration("gh"))
        b = conn.binding_for("git.push")
        assert b is not None
        assert b.action == "push"

    async def test_invoke_success(self) -> None:
        integ = _FakeIntegration("gh")
        conn = GitHubConnector(integ)
        perms = PermissionSet([Permission.PROCESS_EXEC])
        result = await conn.invoke("git.push", perms, repo="x")
        assert result.ok
        assert integ.calls == [("push", {"repo": "x"})]

    async def test_invoke_missing_permission(self) -> None:
        integ = _FakeIntegration("gh")
        conn = GitHubConnector(integ)
        perms = PermissionSet([])  # no perms
        result = await conn.invoke("git.push", perms)
        assert not result.ok
        assert "Missing permissions" in result.error
        assert integ.calls == []  # not executed

    async def test_invoke_unknown_capability(self) -> None:
        conn = GitHubConnector(_FakeIntegration("gh"))
        perms = PermissionSet([Permission.PROCESS_EXEC])
        try:
            await conn.invoke("nope", perms)
            pytest.fail("expected LookupError")
        except LookupError:
            pass


class TestConnectorRegistry:
    def test_register_and_lookup(self) -> None:
        reg = ConnectorRegistry()
        reg.register(GitHubConnector(_FakeIntegration("gh")))
        assert reg.has("github")
        assert reg.get("github") is not None
        assert "github" in reg

    def test_duplicate_raises(self) -> None:
        reg = ConnectorRegistry()
        reg.register(GitHubConnector(_FakeIntegration("gh")))
        try:
            reg.register(GitHubConnector(_FakeIntegration("gh2")))
            pytest.fail("expected ValueError")
        except ValueError:
            pass

    def test_connectors_for_and_route(self) -> None:
        reg = ConnectorRegistry()
        reg.register(GitHubConnector(_FakeIntegration("gh")))
        reg.register(SlackConnector(_FakeIntegration("sl")))
        assert len(reg.connectors_for("git.push")) == 1
        route = reg.route("git.push")
        assert route is not None
        assert route.connector == "github"
        assert route.action == "push"
        assert reg.route("does.not.exist") is None

    def test_unregister_and_clear(self) -> None:
        reg = ConnectorRegistry()
        reg.register(GitHubConnector(_FakeIntegration("gh")))
        assert reg.unregister("github") is not None
        assert reg.count == 0
        assert reg.clear() == 0


class TestGmailConnector:
    def test_bindings(self) -> None:
        conn = GmailConnector(_FakeIntegration("gm"))
        assert conn.can_handle("gmail.send")
        assert conn.can_handle("gmail.read")
        assert conn.can_handle("gmail.draft")
        assert not conn.can_handle("git.push")

    async def test_invoke_send(self) -> None:
        integ = _FakeIntegration("gm")
        conn = GmailConnector(integ)
        perms = PermissionSet([Permission.NETWORK_HTTP])
        result = await conn.invoke("gmail.send", perms, to="x@y.z")
        assert result.ok
        assert integ.calls == [("send_message", {"to": "x@y.z"})]


class TestDockerConnector:
    def test_bindings(self) -> None:
        conn = DockerConnector(_FakeIntegration("dk"))
        assert conn.can_handle("docker.run")
        assert conn.can_handle("docker.build")
        assert conn.can_handle("docker.ps")

    async def test_invoke_run_requires_exec(self) -> None:
        integ = _FakeIntegration("dk")
        conn = DockerConnector(integ)
        perms = PermissionSet([Permission.NETWORK_HTTP])  # no PROCESS_EXEC
        result = await conn.invoke("docker.run", perms, image="alpine")
        assert not result.ok
        assert "Missing permissions" in result.error


class TestFilesystemConnector:
    def test_list_binding(self) -> None:
        conn = FilesystemConnector(_FakeIntegration("fs"))
        assert conn.binding_for("filesystem.list") is not None


class TestBuiltinConnectors:
    def test_register_builtin(self) -> None:
        from aios.integrations.connectors import register_builtin_connectors

        reg = ConnectorRegistry()
        register_builtin_connectors(
            reg,
            {
                "github": _FakeIntegration("gh"),
                "slack": _FakeIntegration("sl"),
                "filesystem": _FakeIntegration("fs"),
                "gmail": _FakeIntegration("gm"),
                "docker": _FakeIntegration("dk"),
            },
        )
        assert reg.has("github")
        assert reg.has("slack")
        assert reg.has("filesystem")
        assert reg.has("gmail")
        assert reg.has("docker")
        assert reg.route("filesystem.read") is not None
        assert reg.route("slack.send") is not None
        assert reg.route("gmail.send") is not None
        assert reg.route("docker.run") is not None
