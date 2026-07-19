"""Base integration — abstract base class for all integrations.

Provides the lifecycle contract: configure → connect → execute → disconnect.
Integrations must subclass Integration and implement the abstract methods.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from aios.integrations.types import (
    HealthCheckResult,
    IntegrationConfig,
    IntegrationResult,
    IntegrationStatus,
)


class Integration(ABC):
    """Abstract base class for service integrations.

    Subclasses must implement:
    - connect(): Establish connection to the service
    - disconnect(): Clean up resources
    - health_check(): Verify connectivity
    - execute(action, **kwargs): Perform an action

    Usage::

        class GitHubIntegration(Integration):
            async def connect(self):
                # Validate credentials
                pass

            async def health_check(self):
                return HealthCheckResult(healthy=True)

            async def execute(self, action, **kwargs):
                if action == "list_repos":
                    return IntegrationResult(ok=True, data={"repos": [...]})
    """

    def __init__(self, config: IntegrationConfig | None = None) -> None:
        self._config = config or IntegrationConfig()
        self._status = IntegrationStatus.DISCOVERED
        self._connected_at: float | None = None
        self._error: str | None = None

    @property
    def name(self) -> str:
        """Integration name from config."""
        return self._config.name or self.__class__.__name__

    @property
    def status(self) -> IntegrationStatus:
        """Current integration status."""
        return self._status

    @property
    def is_connected(self) -> bool:
        """Whether the integration is connected."""
        return self._status == IntegrationStatus.CONNECTED

    @property
    def config(self) -> IntegrationConfig:
        """Integration configuration."""
        return self._config

    @property
    def uptime_seconds(self) -> float:
        """Time since last connection, or 0 if not connected."""
        if self._connected_at is None:
            return 0.0
        return time.monotonic() - self._connected_at

    def configure(self, config: IntegrationConfig) -> None:
        """Update configuration. Must be done before connecting."""
        if self._status == IntegrationStatus.CONNECTED:
            raise RuntimeError("Cannot reconfigure while connected")
        self._config = config
        self._status = IntegrationStatus.CONFIGURED

    async def initialize(self) -> IntegrationResult:
        """Full lifecycle: configure → connect.

        Convenience method that combines configuration validation and connection.
        """
        try:
            self._status = IntegrationStatus.CONNECTING
            await self.connect()
            self._status = IntegrationStatus.CONNECTED
            self._connected_at = time.monotonic()
            self._error = None
            return IntegrationResult(ok=True, status=IntegrationStatus.CONNECTED)
        except Exception as exc:
            self._status = IntegrationStatus.ERROR
            self._error = str(exc)
            return IntegrationResult(
                ok=False,
                error=str(exc),
                status=IntegrationStatus.ERROR,
            )

    async def shutdown(self) -> IntegrationResult:
        """Disconnect and clean up resources."""
        try:
            self._status = IntegrationStatus.DISCONNECTING
            await self.disconnect()
            self._status = IntegrationStatus.DISABLED
            self._connected_at = None
            self._error = None
            return IntegrationResult(ok=True, status=IntegrationStatus.DISABLED)
        except Exception as exc:
            self._status = IntegrationStatus.ERROR
            self._error = str(exc)
            return IntegrationResult(
                ok=False,
                error=str(exc),
                status=IntegrationStatus.ERROR,
            )

    async def safe_execute(self, action: str, **kwargs: object) -> IntegrationResult:
        """Execute with automatic reconnection on failure.

        Tries execute(), and if it fails, attempts to reconnect once
        before retrying.
        """
        if not self.is_connected:
            return IntegrationResult(
                ok=False,
                error=f"Integration '{self.name}' is not connected (status: {self._status.value})",
                status=self._status,
            )
        result = await self.execute(action, **kwargs)
        if not result.ok and self._status == IntegrationStatus.CONNECTED:
            # Try reconnect once
            reconnect = await self.initialize()
            if reconnect.ok:
                result = await self.execute(action, **kwargs)
        return result

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the service.

        Raises:
            ConnectionError: If connection fails.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Clean up connection resources."""

    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        """Verify the integration is healthy and reachable."""

    @abstractmethod
    async def execute(self, action: str, **kwargs: object) -> IntegrationResult:
        """Execute an integration action.

        Args:
            action: Action name (e.g. "list_repos", "send_message").
            **kwargs: Action-specific parameters.

        Returns:
            IntegrationResult with the action output.
        """

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} name={self.name!r} "
            f"status={self._status.value}>"
        )


__all__ = [
    "Integration",
]
