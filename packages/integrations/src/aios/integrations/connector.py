"""Connector — binds a capability to one or more integration operations.

A **connector** is the ADR-0019 bridge between the capability catalog and the
external world. Where an :class:`~aios.integrations.base.Integration` owns a
single external system (GitHub, Slack, …), a **connector** declares *which
capabilities* it can satisfy and *routes* an invocation to the right integration
action.

This module does NOT replace :class:`Integration`; it composes over it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aios.agents.permissions import PermissionSet
    from aios.integrations.base import Integration
    from aios.integrations.types import IntegrationResult


@dataclass(frozen=True)
class ConnectorBinding:
    """Maps a capability to a concrete integration action.

    Attributes:
        capability: Catalog capability name this binding satisfies.
        action: The integration action string to call.
        required_permissions: Frozen permissions needed for this binding.
        description: Human-readable description.
    """

    capability: str
    action: str
    required_permissions: tuple[str, ...] = ()
    description: str = ""


class Connector(ABC):
    """Abstract connector: capability → integration operation router.

    Subclasses declare their :meth:`bindings` and are constructed with the
    :class:`Integration` they drive.
    """

    def __init__(self, integration: Integration, name: str | None = None) -> None:
        self._integration = integration
        self._name = name or self.__class__.__name__

    @property
    def name(self) -> str:
        """Connector name."""
        return self._name

    @property
    def integration(self) -> Integration:
        """The backing integration instance."""
        return self._integration

    @abstractmethod
    def bindings(self) -> list[ConnectorBinding]:
        """Return the capability→action bindings this connector provides."""

    # -- routing -----------------------------------------------------------

    def capabilities(self) -> list[str]:
        """All capability names this connector can satisfy."""
        return [b.capability for b in self.bindings()]

    def binding_for(self, capability: str) -> ConnectorBinding | None:
        """Return the binding for a capability, if provided."""
        for b in self.bindings():
            if b.capability == capability:
                return b
        return None

    def can_handle(self, capability: str) -> bool:
        """Whether this connector handles the given capability."""
        return self.binding_for(capability) is not None

    def authorized(self, capability: str, perms: PermissionSet) -> bool:
        """Whether the granted permissions satisfy the binding's requirements."""
        binding = self.binding_for(capability)
        if binding is None:
            return False
        return perms.has_all(binding.required_permissions)

    async def invoke(
        self,
        capability: str,
        perms: PermissionSet,
        **params: object,
    ) -> IntegrationResult:
        """Route a capability invocation to the backing integration.

        Raises:
            LookupError: If the connector does not handle the capability.
            PermissionError: If required permissions are not granted.
        """
        from aios.integrations.types import IntegrationResult

        binding = self.binding_for(capability)
        if binding is None:
            raise LookupError(
                f"Connector '{self._name}' cannot handle '{capability}'"
            )
        if not self.authorized(capability, perms):
            return IntegrationResult(
                ok=False,
                error=(
                    f"Missing permissions for '{capability}': "
                    f"{binding.required_permissions}"
                ),
            )
        return await self._integration.safe_execute(binding.action, **params)


@dataclass
class ConnectorRoute:
    """A resolved route from capability → connector → binding."""

    connector: str
    capability: str
    action: str
    required_permissions: tuple[str, ...] = ()


class ConnectorRegistry:
    """Registry of connectors keyed by name, with capability-based lookup."""

    def __init__(self) -> None:
        self._connectors: dict[str, Connector] = {}

    def register(self, connector: Connector) -> None:
        """Register a connector. Raises if name already registered."""
        if connector.name in self._connectors:
            raise ValueError(f"Connector '{connector.name}' already registered")
        self._connectors[connector.name] = connector

    def unregister(self, name: str) -> Connector | None:
        """Remove a connector by name."""
        return self._connectors.pop(name, None)

    def get(self, name: str) -> Connector | None:
        """Get a connector by name."""
        return self._connectors.get(name)

    def has(self, name: str) -> bool:
        """Whether a connector is registered."""
        return name in self._connectors

    def connectors_for(self, capability: str) -> list[Connector]:
        """Return connectors that can handle a capability."""
        return [c for c in self._connectors.values() if c.can_handle(capability)]

    def route(self, capability: str) -> ConnectorRoute | None:
        """Resolve the first connector that handles a capability."""
        for connector in self._connectors.values():
            binding = connector.binding_for(capability)
            if binding is not None:
                return ConnectorRoute(
                    connector=connector.name,
                    capability=capability,
                    action=binding.action,
                    required_permissions=binding.required_permissions,
                )
        return None

    @property
    def names(self) -> list[str]:
        """Registered connector names."""
        return list(self._connectors.keys())

    @property
    def count(self) -> int:
        """Number of registered connectors."""
        return len(self._connectors)

    def clear(self) -> int:
        """Remove all connectors. Returns count removed."""
        count = len(self._connectors)
        self._connectors.clear()
        return count

    def __contains__(self, name: str) -> bool:
        return name in self._connectors

    def __len__(self) -> int:
        return len(self._connectors)


__all__ = [
    "Connector",
    "ConnectorBinding",
    "ConnectorRegistry",
    "ConnectorRoute",
]
