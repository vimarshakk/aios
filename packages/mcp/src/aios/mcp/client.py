"""AIOS MCP layer — Model Context Protocol as a *transport* (ADR-0019).

Per ADR-0019, MCP is **transport only**, not a framework. AIOS uses MCP to
bridge external tool servers: an :class:`MCPClient` connects to an MCP server
over a pluggable :class:`MCPTransport`, discovers its tools, and exposes them
as capabilities that are gated by the frozen permission model.

The transport is abstracted behind a protocol so the layer is fully testable
without a live MCP server or the ``mcp`` SDK installed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aios.agents.permissions import PermissionSet


@dataclass(frozen=True)
class MCPToolSpec:
    """Specification of a tool exposed by an MCP server."""

    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    required_permission: str | None = None


class MCPTransport(ABC):
    """Abstract transport to an MCP server.

    Implementations wrap the real ``mcp`` SDK session. The default in-process
    test double is :class:`StubTransport`.
    """

    @abstractmethod
    async def list_tools(self) -> list[MCPToolSpec]:
        """Return the tools advertised by the server."""

    @abstractmethod
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Invoke a tool and return its raw result."""


class StubTransport(MCPTransport):
    """In-memory transport for tests and local tool servers."""

    def __init__(self, tools: list[MCPToolSpec] | None = None) -> None:
        self._tools = tools or []
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def list_tools(self) -> list[MCPToolSpec]:
        return list(self._tools)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((name, arguments))
        for t in self._tools:
            if t.name == name:
                return {"tool": name, "arguments": arguments, "ok": True}
        raise KeyError(f"Unknown MCP tool: {name}")


@dataclass
class MCPServerConfig:
    """Connection config for an MCP server."""

    name: str
    transport: str = "stdio"  # "stdio" | "sse" | "stub"
    command: list[str] | None = None
    url: str | None = None


class MCPClient:
    """Client for a single MCP server. Lists and invokes tools over transport."""

    def __init__(
        self,
        config: MCPServerConfig,
        transport: MCPTransport,
    ) -> None:
        self._config = config
        self._transport = transport
        self._cached: list[MCPToolSpec] | None = None

    @property
    def name(self) -> str:
        """Server name."""
        return self._config.name

    async def list_tools(self) -> list[MCPToolSpec]:
        """List tools, caching the result."""
        if self._cached is None:
            self._cached = await self._transport.list_tools()
        return self._cached

    async def call(
        self,
        name: str,
        arguments: dict[str, Any],
        perms: PermissionSet | None = None,
    ) -> Any:
        """Call a tool, enforcing its required permission if provided."""
        spec = next((t for t in await self.list_tools() if t.name == name), None)
        if spec is None:
            raise KeyError(f"Tool '{name}' not found on server '{self.name}'")
        if spec.required_permission and perms is not None and not perms.has(
            spec.required_permission
        ):
            raise PermissionError(
                f"Permission '{spec.required_permission}' required for tool '{name}'"
            )
        return await self._transport.call_tool(name, arguments)


class MCPRegistry:
    """Aggregates multiple MCP clients and resolves tools by name."""

    def __init__(self) -> None:
        self._clients: dict[str, MCPClient] = {}

    def register(self, client: MCPClient) -> None:
        """Register an MCP client by server name."""
        self._clients[client.name] = client

    def unregister(self, name: str) -> None:
        """Remove a client by server name."""
        self._clients.pop(name, None)

    def get(self, name: str) -> MCPClient | None:
        """Get a client by server name."""
        return self._clients.get(name)

    @property
    def servers(self) -> list[str]:
        """Registered server names."""
        return list(self._clients.keys())

    async def discover_tools(self) -> dict[str, list[MCPToolSpec]]:
        """Return a mapping of server name → tool specs."""
        out: dict[str, list[MCPToolSpec]] = {}
        for name, client in self._clients.items():
            out[name] = await client.list_tools()
        return out

    async def call_tool(
        self,
        server: str,
        name: str,
        arguments: dict[str, Any],
        perms: PermissionSet | None = None,
    ) -> Any:
        """Route a tool call to the named server."""
        client = self._clients.get(server)
        if client is None:
            raise KeyError(f"Unknown MCP server: {server}")
        return await client.call(name, arguments, perms)


__all__ = [
    "MCPClient",
    "MCPRegistry",
    "MCPServerConfig",
    "MCPToolSpec",
    "MCPTransport",
    "StubTransport",
]
