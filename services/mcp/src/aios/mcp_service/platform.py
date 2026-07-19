"""AIOS MCP platform — service-level registry, discovery, and permission gating.

This module (``aios.mcp_service``) composes the transport-only
:mod:`aios.mcp` library (ADR-0019) into a service surface. It:

* maintains an :class:`~aios.mcp.client.MCPRegistry` of connected servers,
* exposes **discovery** (server → tools, cached) for the gateway,
* enforces the **frozen permission model** on every tool call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aios.mcp import MCPClient, MCPRegistry, MCPServerConfig, MCPToolSpec, StubTransport

if TYPE_CHECKING:
    from aios.agents.permissions import PermissionSet


class MCPPlatform:
    """Service surface over one or more MCP servers.

    Args:
        registry: Optional pre-built registry (defaults to a new one).
    """

    def __init__(self, registry: MCPRegistry | None = None) -> None:
        self._registry = registry or MCPRegistry()
        self._discovery_cache: dict[str, list[MCPToolSpec]] | None = None

    @property
    def registry(self) -> MCPRegistry:
        """Underlying server registry."""
        return self._registry

    # -- registration ------------------------------------------------------

    def add_server(
        self,
        config: MCPServerConfig | str,
        tools: list[MCPToolSpec] | None = None,
    ) -> MCPClient:
        """Register a server backed by a :class:`StubTransport` with ``tools``.

        ``config`` may be a full :class:`MCPServerConfig` or a plain server
        name string (an stdio config is created from it).

        For real servers, provide a custom :class:`~aios.mcp.client.MCPTransport`
        via :meth:`aios.mcp.client.MCPClient` directly and ``register`` it.
        """
        if isinstance(config, str):
            config = MCPServerConfig(name=config)
        transport = StubTransport(tools or [])
        client = MCPClient(config, transport)
        self._registry.register(client)
        self._discovery_cache = None
        return client

    @property
    def servers(self) -> list[str]:
        """Registered server names."""
        return self._registry.servers

    # -- discovery ---------------------------------------------------------

    async def discover(self, refresh: bool = False) -> dict[str, list[MCPToolSpec]]:
        """Return server → tool specs, using a cached result unless ``refresh``."""
        if self._discovery_cache is not None and not refresh:
            return self._discovery_cache
        result = await self._registry.discover_tools()
        self._discovery_cache = result
        return result

    async def tools_for(self, server: str) -> list[MCPToolSpec]:
        """Return the tool specs for a single server (discovery-aware)."""
        discovered = await self.discover()
        return discovered.get(server, [])

    # -- permission-gated invocation ---------------------------------------

    async def call(
        self,
        server: str,
        tool: str,
        arguments: dict[str, Any],
        perms: PermissionSet | None = None,
    ) -> Any:
        """Call a tool on a server, enforcing the frozen permission model."""
        return await self._registry.call_tool(server, tool, arguments, perms)


__all__ = [
    "MCPPlatform",
]
