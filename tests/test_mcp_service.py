"""Tests for aios.mcp_service.platform — registry, discovery, permissions."""

from __future__ import annotations

import pytest

from aios.agents.permissions import Permission, PermissionSet
from aios.mcp import MCPToolSpec
from aios.mcp_service.platform import MCPPlatform


def _make() -> MCPPlatform:
    p = MCPPlatform()
    p.add_server(
        "local",
        tools=[
            MCPToolSpec(name="echo", description="echo", required_permission="network.http"),
            MCPToolSpec(name="run", description="run", required_permission="process.exec"),
        ],
    )
    return p


class TestMCPPlatform:
    def test_add_server_registers(self) -> None:
        p = _make()
        assert "local" in p.servers
        assert len(p.registry.servers) == 1

    async def test_discover(self) -> None:
        p = _make()
        discovered = await p.discover()
        assert "local" in discovered
        names = {t.name for t in discovered["local"]}
        assert names == {"echo", "run"}

    async def test_discover_caches(self) -> None:
        p = _make()
        first = await p.discover()
        second = await p.discover()
        assert first is second  # cached object identity

    async def test_discover_refresh(self) -> None:
        p = _make()
        first = await p.discover()
        second = await p.discover(refresh=True)
        assert first == second

    async def test_tools_for(self) -> None:
        p = _make()
        specs = await p.tools_for("local")
        assert len(specs) == 2

    async def test_call_permission_gated(self) -> None:
        p = _make()
        # echo requires network.http
        await p.call("local", "echo", {"x": 1}, perms=PermissionSet([Permission.NETWORK_HTTP]))
        # run requires process.exec -> missing should raise
        with pytest.raises(PermissionError):
            await p.call("local", "run", {}, perms=PermissionSet([Permission.NETWORK_HTTP]))

    async def test_call_unknown_server(self) -> None:
        p = _make()
        with pytest.raises(KeyError, match="Unknown MCP server"):
            await p.call("nope", "echo", {})
