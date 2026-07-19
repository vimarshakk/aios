"""Tests for the Composio connector and integration."""

from __future__ import annotations

from aios.agents.permissions import Permission, PermissionSet
from aios.integrations.composio import (
    DEFAULT_ENTITY,
    ComposioConnector,
    ComposioIntegration,
)
from aios.integrations.types import IntegrationStatus


class _FakeComposioClient:
    """Minimal in-memory stand-in for the Composio SDK client."""

    def __init__(self) -> None:
        self.executed: list[tuple[str, str, dict]] = []

    def tools_execute(self, user_id: str, slug: str, arguments: dict) -> dict:
        self.executed.append((user_id, slug, arguments))
        return {"executed": slug, "user_id": user_id, "args": arguments}

    # The real SDK exposes ``client.tools.execute``; emulate that shape.
    class _Tools:
        def __init__(self, parent: _FakeComposioClient) -> None:
            self._parent = parent

        def execute(self, user_id: str, slug: str, arguments: dict) -> dict:
            return self._parent.tools_execute(user_id, slug, arguments)

        def get(self, user_id: str, toolkits: list[str]) -> dict:
            # Emulate discovery returning a list of tool specs.
            return [
                {
                    "slug": "GITHUB_STAR_REPO",
                    "name": "GITHUB_STAR_REPO",
                    "description": "Star a repository",
                }
            ]

    @property
    def tools(self) -> _Tools:
        return _FakeComposioClient._Tools(self)


def _make_connector() -> ComposioConnector:
    integration = ComposioIntegration(api_key="test", entity="tester")
    # Inject a fake client so no real SDK / network is needed.
    integration._client = _FakeComposioClient()  # type: ignore[assignment]
    integration._status = IntegrationStatus.CONNECTED
    return ComposioConnector(integration)


def test_curated_bindings_present() -> None:
    connector = _make_connector()
    caps = {b.capability for b in connector.bindings()}
    assert "composio.github" in caps
    assert "composio.notion" in caps
    assert "composio.gmail" in caps
    assert "composio.slack" in caps
    assert "composio.linear" in caps
    assert all(b.required_permissions == (Permission.NETWORK_HTTP,) for b in connector.bindings())


def test_toolkit_for_and_curated_toolkits() -> None:
    connector = _make_connector()
    assert connector.toolkit_for("composio.github") == "github"
    assert connector.toolkit_for("composio.notion") == "notion"
    assert connector.toolkit_for("composio.unknown") is None
    assert set(connector.curated_toolkits) == {
        "github",
        "notion",
        "gmail",
        "slack",
        "linear",
    }


async def test_invoke_curated_capability() -> None:
    connector = _make_connector()
    perms = PermissionSet(granted=[Permission.NETWORK_HTTP])
    result = await connector.invoke(
        "composio.github", perms, title="Bug", body="repro"
    )
    assert result.ok is True
    assert result.status == IntegrationStatus.CONNECTED
    client = connector._integration._client  # type: ignore[attr-defined]
    assert client.executed[-1][1] == "GITHUB_CREATE_ISSUE"


async def test_invoke_dynamic_action() -> None:
    connector = _make_connector()
    perms = PermissionSet(granted=[Permission.NETWORK_HTTP])
    result = await connector.invoke(
        "composio.dynamic", perms, action="GITHUB_STAR_REPO", repo="a/b"
    )
    assert result.ok is True
    client = connector._integration._client  # type: ignore[attr-defined]
    assert client.executed[-1][1] == "GITHUB_STAR_REPO"


async def test_invoke_missing_permission_denied() -> None:
    connector = _make_connector()
    perms = PermissionSet(granted=[])  # no network.http
    result = await connector.invoke("composio.github", perms, title="x")
    assert result.ok is False
    assert "network.http" in (result.error or "")


async def test_invoke_unknown_capability_without_action() -> None:
    connector = _make_connector()
    perms = PermissionSet(granted=[Permission.NETWORK_HTTP])
    result = await connector.invoke("composio.unknown", perms)
    assert result.ok is False
    assert "action=" in (result.error or "")


async def test_discover_uses_client_tools_get() -> None:
    connector = _make_connector()
    tools = await connector.discover(toolkits=["github"])
    assert any(t["slug"] == "GITHUB_STAR_REPO" for t in tools)
    assert all(t["toolkit"] == "github" for t in tools)


def test_default_entity_constant() -> None:
    assert DEFAULT_ENTITY == "default"
