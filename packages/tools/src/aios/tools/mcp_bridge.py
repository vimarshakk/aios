"""MCP (Model Context Protocol) bridge — connect to any MCP server as a tool.

Extracted from OpenJarvis MCP patterns + LibreChat MCP integration.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from aios.agents.types import ToolResult


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server to connect to."""
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None


class MCPBridge:
    """Connect to MCP servers and expose their tools as AIOS tools."""

    def __init__(self) -> None:
        self._sessions: dict[str, ClientSession] = {}
        self._tools: dict[str, dict[str, Any]] = {}

    async def connect_server(self, config: MCPServerConfig) -> list[dict[str, Any]]:
        """Connect to an MCP server and discover its tools."""
        params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env,
        )
        read_stream, write_stream = await stdio_client(params).__aenter__()
        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        await session.initialize()
        self._sessions[config.name] = session

        tools_result = await session.list_tools()
        discovered = []
        for tool in tools_result.tools:
            tool_info = {
                "server": config.name,
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema if hasattr(tool, "inputSchema") else {},
            }
            self._tools[f"{config.name}/{tool.name}"] = tool_info
            discovered.append(tool_info)
        return discovered

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolResult:
        """Call a tool on a connected MCP server."""
        import time
        t0 = time.monotonic()
        key = f"{server_name}/{tool_name}"
        if key not in self._tools:
            return ToolResult(
                tool_name=key,
                content=f"Tool {key} not found",
                success=False,
                latency_seconds=time.monotonic() - t0,
            )

        session = self._sessions.get(server_name)
        if not session:
            return ToolResult(
                tool_name=key,
                content=f"Server {server_name} not connected",
                success=False,
                latency_seconds=time.monotonic() - t0,
            )

        try:
            result = await session.call_tool(tool_name, arguments)
            content = ""
            if hasattr(result, "content") and result.content:
                for block in result.content:
                    if hasattr(block, "text"):
                        content += block.text
            return ToolResult(
                tool_name=key,
                content=content or str(result),
                latency_seconds=time.monotonic() - t0,
            )
        except Exception as e:
            return ToolResult(
                tool_name=key,
                content=f"Error calling {key}: {e}",
                success=False,
                latency_seconds=time.monotonic() - t0,
            )

    def list_tools(self) -> list[dict[str, Any]]:
        return list(self._tools.values())

    async def disconnect_all(self) -> None:
        for session in self._sessions.values():
            with contextlib.suppress(Exception):
                await session.__aexit__(None, None, None)
        self._sessions.clear()
        self._tools.clear()


__all__ = ["MCPBridge", "MCPServerConfig"]
