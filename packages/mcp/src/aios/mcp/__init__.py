"""AIOS MCP layer — MCP as a transport (ADR-0019)."""

from aios.mcp.client import (
    MCPClient,
    MCPRegistry,
    MCPServerConfig,
    MCPToolSpec,
    MCPTransport,
    StubTransport,
)
from aios.mcp.mapping import DEFAULT_TOOL_PERMISSIONS, permission_for_tool

API_VERSION = "1.0"

__all__ = [
    "API_VERSION",
    "DEFAULT_TOOL_PERMISSIONS",
    "MCPClient",
    "MCPRegistry",
    "MCPServerConfig",
    "MCPToolSpec",
    "MCPTransport",
    "StubTransport",
    "permission_for_tool",
]
