"""Tests for MCPBridge."""

import pytest

from aios.tools.mcp_bridge import MCPBridge, MCPServerConfig


class TestMCPServerConfig:
    def test_construction(self):
        config = MCPServerConfig(name="test", command="echo")
        assert config.name == "test"
        assert config.args == []
        assert config.env is None

    def test_with_args(self):
        config = MCPServerConfig(
            name="test",
            command="python",
            args=["-m", "server"],
            env={"KEY": "value"},
        )
        assert config.args == ["-m", "server"]
        assert config.env == {"KEY": "value"}


class TestMCPBridge:
    def test_construction(self):
        bridge = MCPBridge()
        assert bridge.list_tools() == []

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self):
        bridge = MCPBridge()
        result = await bridge.call_tool("nonexistent", "tool", {})
        assert result.success is False
        assert "not found" in result.content.lower()

    @pytest.mark.asyncio
    async def test_disconnect_all_empty(self):
        bridge = MCPBridge()
        await bridge.disconnect_all()
        assert bridge.list_tools() == []
