"""Declarative permission mapping for MCP tools.

MCP servers advertise tools without AIOS permission context. This module maps
well-known tool names to frozen :class:`aios.agents.permissions.Permission`
values so the :class:`~aios.mcp.client.MCPClient` can enforce them.
"""

from __future__ import annotations

from aios.agents.permissions import Permission

# Default mapping of common MCP tool names → required frozen permission.
DEFAULT_TOOL_PERMISSIONS: dict[str, str] = {
    "filesystem_read": Permission.FILESYSTEM_READ,
    "filesystem_write": Permission.FILESYSTEM_WRITE,
    "shell_exec": Permission.PROCESS_EXEC,
    "web_search": Permission.NETWORK_HTTP,
    "web_fetch": Permission.NETWORK_HTTP,
    "screenshot": Permission.SCREEN_CAPTURE,
    "db_query": Permission.DATABASE_READ,
    "db_write": Permission.DATABASE_WRITE,
}


def permission_for_tool(
    tool_name: str,
    overrides: dict[str, str] | None = None,
) -> str | None:
    """Resolve the required permission for a tool name.

    Args:
        tool_name: The MCP tool name.
        overrides: Optional per-tool overrides merged over the defaults.
    """
    mapping = DEFAULT_TOOL_PERMISSIONS.copy()
    if overrides:
        mapping.update(overrides)
    return mapping.get(tool_name)


__all__ = ["DEFAULT_TOOL_PERMISSIONS", "permission_for_tool"]
