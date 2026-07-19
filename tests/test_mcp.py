"""Tests for aios.mcp — client, registry, transport, permission mapping."""

from __future__ import annotations

import pytest

from aios.agents.permissions import Permission, PermissionSet
from aios.mcp import (
    MCPClient,
    MCPRegistry,
    MCPServerConfig,
    MCPToolSpec,
    StubTransport,
    permission_for_tool,
)
from aios.mcp.mapping import DEFAULT_TOOL_PERMISSIONS


class TestStubTransport:
    async def test_list_and_call(self) -> None:
        t = StubTransport(
            [MCPToolSpec(name="echo", description="echo")]
        )
        tools = await t.list_tools()
        assert tools[0].name == "echo"
        result = await t.call_tool("echo", {"msg": "hi"})
        assert result["ok"] is True
        assert t.calls == [("echo", {"msg": "hi"})]

    async def test_unknown_tool(self) -> None:
        t = StubTransport([])
        try:
            await t.call_tool("x", {})
            pytest.fail("expected KeyError")
        except KeyError:
            pass


class TestMCPClient:
    async def test_list_tools_caches(self) -> None:
        t = StubTransport([MCPToolSpec(name="a"), MCPToolSpec(name="b")])
        client = MCPClient(MCPServerConfig(name="srv"), t)
        assert [x.name for x in await client.list_tools()] == ["a", "b"]
        assert [x.name for x in await client.list_tools()] == ["a", "b"]

    async def test_call_success(self) -> None:
        t = StubTransport([MCPToolSpec(name="echo")])
        client = MCPClient(MCPServerConfig(name="srv"), t)
        result = await client.call("echo", {"x": 1})
        assert result["ok"] is True

    async def test_call_unknown_tool(self) -> None:
        t = StubTransport([])
        client = MCPClient(MCPServerConfig(name="srv"), t)
        try:
            await client.call("nope", {})
            pytest.fail("expected KeyError")
        except KeyError:
            pass

    async def test_call_permission_enforced(self) -> None:
        t = StubTransport(
            [MCPToolSpec(name="write", required_permission=Permission.FILESYSTEM_WRITE)]
        )
        client = MCPClient(MCPServerConfig(name="srv"), t)
        with pytest.raises(PermissionError):
            await client.call("write", {}, perms=PermissionSet([]))
        result = await client.call(
            "write", {}, perms=PermissionSet([Permission.FILESYSTEM_WRITE])
        )
        assert result["ok"] is True

    async def test_call_no_perms_arg_skips_check(self) -> None:
        t = StubTransport(
            [MCPToolSpec(name="write", required_permission=Permission.FILESYSTEM_WRITE)]
        )
        client = MCPClient(MCPServerConfig(name="srv"), t)
        result = await client.call("write", {})
        assert result["ok"] is True


class TestMCPRegistry:
    async def test_register_and_discover(self) -> None:
        reg = MCPRegistry()
        t = StubTransport([MCPToolSpec(name="echo")])
        reg.register(MCPClient(MCPServerConfig(name="srv"), t))
        assert "srv" in reg.servers
        discovered = await reg.discover_tools()
        assert [x.name for x in discovered["srv"]] == ["echo"]

    async def test_route_call(self) -> None:
        reg = MCPRegistry()
        t = StubTransport([MCPToolSpec(name="echo")])
        reg.register(MCPClient(MCPServerConfig(name="srv"), t))
        result = await reg.call_tool("srv", "echo", {"a": 1})
        assert result["ok"] is True

    async def test_route_unknown_server(self) -> None:
        reg = MCPRegistry()
        try:
            await reg.call_tool("ghost", "echo", {})
            pytest.fail("expected KeyError")
        except KeyError:
            pass

    def test_unregister(self) -> None:
        reg = MCPRegistry()
        reg.register(MCPClient(MCPServerConfig(name="srv"), StubTransport()))
        reg.unregister("srv")
        assert reg.servers == []


class TestPermissionMapping:
    def test_defaults(self) -> None:
        assert DEFAULT_TOOL_PERMISSIONS["filesystem_read"] == Permission.FILESYSTEM_READ
        assert DEFAULT_TOOL_PERMISSIONS["shell_exec"] == Permission.PROCESS_EXEC

    def test_permission_for_tool(self) -> None:
        assert permission_for_tool("web_fetch") == Permission.NETWORK_HTTP
        assert permission_for_tool("unknown") is None
        assert (
            permission_for_tool("unknown", {"unknown": Permission.VOICE_RECORD})
            == Permission.VOICE_RECORD
        )
