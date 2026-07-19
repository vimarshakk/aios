"""Integration registry — discovery, lifecycle, and lookup for integrations.

Maintains a mapping of integration names to their instances and provides
methods for registering, connecting, disconnecting, and querying integrations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from aios.integrations.types import IntegrationStatus

if TYPE_CHECKING:
    from aios.integrations.base import Integration


@dataclass(frozen=True)
class RegistryStats:
    """Snapshot of registry state."""

    total: int = 0
    connected: int = 0
    errored: int = 0
    disabled: int = 0


class IntegrationRegistry:
    """Manages integration instances.

    Usage::

        registry = IntegrationRegistry()
        registry.register(GitHubIntegration(config))
        registry.register(SlackIntegration(config))
        await registry.connect_all()
        stats = registry.stats()
        # stats.total == 2
        await registry.disconnect_all()
    """

    def __init__(self) -> None:
        self._integrations: dict[str, Integration] = {}

    def register(self, integration: Integration) -> None:
        """Register an integration instance.

        Raises:
            ValueError: If an integration with the same name already exists.
        """
        name = integration.name
        if name in self._integrations:
            raise ValueError(f"Integration '{name}' already registered")
        self._integrations[name] = integration

    def unregister(self, name: str) -> Integration | None:
        """Remove and return an integration by name.

        Returns None if not found.
        """
        return self._integrations.pop(name, None)

    def get(self, name: str) -> Integration | None:
        """Get an integration by name."""
        return self._integrations.get(name)

    def has(self, name: str) -> bool:
        """Check if an integration is registered."""
        return name in self._integrations

    @property
    def names(self) -> list[str]:
        """List of registered integration names."""
        return list(self._integrations.keys())

    @property
    def count(self) -> int:
        """Number of registered integrations."""
        return len(self._integrations)

    def all(self) -> list[Integration]:
        """Return all registered integrations."""
        return list(self._integrations.values())

    def by_status(self, status: IntegrationStatus) -> list[Integration]:
        """Return integrations matching a given status."""
        return [i for i in self._integrations.values() if i.status == status]

    def connected(self) -> list[Integration]:
        """Return all connected integrations."""
        return self.by_status(IntegrationStatus.CONNECTED)

    def errored(self) -> list[Integration]:
        """Return all integrations in error state."""
        return self.by_status(IntegrationStatus.ERROR)

    async def connect_all(self) -> dict[str, bool]:
        """Connect all registered integrations.

        Returns:
            Dict mapping integration names to connection success (True/False).
        """
        results: dict[str, bool] = {}
        for name, integration in self._integrations.items():
            result = await integration.initialize()
            results[name] = result.ok
        return results

    async def disconnect_all(self) -> dict[str, bool]:
        """Disconnect all registered integrations.

        Returns:
            Dict mapping integration names to disconnect success.
        """
        results: dict[str, bool] = {}
        for name, integration in self._integrations.items():
            result = await integration.shutdown()
            results[name] = result.ok
        return results

    def stats(self) -> RegistryStats:
        """Current registry statistics."""
        total = len(self._integrations)
        connected = sum(
            1 for i in self._integrations.values()
            if i.status == IntegrationStatus.CONNECTED
        )
        errored = sum(
            1 for i in self._integrations.values()
            if i.status == IntegrationStatus.ERROR
        )
        disabled = sum(
            1 for i in self._integrations.values()
            if i.status == IntegrationStatus.DISABLED
        )
        return RegistryStats(total=total, connected=connected, errored=errored, disabled=disabled)

    def clear(self) -> int:
        """Remove all integrations. Returns count removed."""
        count = len(self._integrations)
        self._integrations.clear()
        return count

    def __contains__(self, name: str) -> bool:
        return name in self._integrations

    def __len__(self) -> int:
        return len(self._integrations)

    def __repr__(self) -> str:
        return f"<IntegrationRegistry count={len(self._integrations)}>"


__all__ = [
    "IntegrationRegistry",
    "RegistryStats",
]
