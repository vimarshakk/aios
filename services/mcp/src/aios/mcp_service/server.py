"""AIOS MCP Server — expose all tools via Model Context Protocol.

This turns AIOS into an MCP server that any MCP client
(Claude Desktop, Continue, LibreChat, etc.) can connect to.

Tools exposed:
    filesystem  — read/write/list files in sandbox
    shell       — execute bash/python commands
    web_search  — search the web (DuckDuckGo)
    web_fetch   — fetch URL content
    memory      — store/retrieve memories
    calculator  — evaluate expressions
    screenshot  — take screenshots
    datetime    — get current time

Usage:
    uv run python -m aios.mcp_service.server
    or add to MCP client config:
    {
      "mcpServers": {
        "aios": {
          "command": "uv",
          "args": ["run", "python", "-m", "aios.mcp_service.server"]
        }
      }
    }
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

# ---------------------------------------------------------------------------
# MCP server using the official mcp SDK
# ---------------------------------------------------------------------------


async def main() -> None:
    """Run the AIOS MCP server on stdio."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent, Tool
    except ImportError:
        print("ERROR: mcp package not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    from aios.tools.builtin import (
        CalculatorTool,
        DateTimeTool,
        FileSystemTool,
        MemoryTool,
        ScreenshotTool,
        ShellExecuteTool,
        WebFetchTool,
        WebSearchTool,
    )

    server = Server("aios")

    # Map tool name → instance
    _tools: dict[str, Any] = {
        "filesystem":   FileSystemTool(),
        "shell":        ShellExecuteTool(),
        "web_search":   WebSearchTool(),
        "web_fetch":    WebFetchTool(),
        "memory":       MemoryTool(),
        "calculator":   CalculatorTool(),
        "screenshot":   ScreenshotTool(),
        "datetime":     DateTimeTool(),
    }

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        result = []
        for tool_instance in _tools.values():
            spec = tool_instance.spec
            # Build JSON Schema for parameters
            properties: dict[str, Any] = {}
            for param_name, param_info in spec.parameters.items():
                prop: dict[str, Any] = {"type": param_info.get("type", "string")}
                if "description" in param_info:
                    prop["description"] = param_info["description"]
                if "enum" in param_info:
                    prop["enum"] = param_info["enum"]
                properties[param_name] = prop

            result.append(Tool(
                name=spec.name,
                description=spec.description,
                inputSchema={
                    "type": "object",
                    "properties": properties,
                    "required": spec.required,
                },
            ))
        return result

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        tool_instance = _tools.get(name)
        if tool_instance is None:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        try:
            result = await tool_instance.execute(**arguments)
            status = "" if result.success else "❌ "
            return [TextContent(type="text", text=f"{status}{result.content}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Tool error: {e}")]

    # Run on stdio (standard MCP transport)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
