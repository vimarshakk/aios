"""Integration types — shared types for the integrations platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class IntegrationStatus(StrEnum):
    """Integration lifecycle status."""

    DISCOVERED = "discovered"
    CONFIGURED = "configured"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    DISABLED = "disabled"
    DISCONNECTING = "disconnecting"


@dataclass(frozen=True)
class IntegrationResult:
    """Result of an integration operation.

    Attributes:
        ok: Whether the operation succeeded.
        data: Response data (if any).
        error: Error message if failed.
        status: Current integration status after the operation.
    """

    ok: bool
    data: dict | None = None
    error: str | None = None
    status: IntegrationStatus = IntegrationStatus.DISCOVERED


@dataclass(frozen=True)
class IntegrationConfig:
    """Configuration for an integration.

    Attributes:
        name: Integration name.
        api_key: API key or token.
        base_url: Base URL for API calls.
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts.
        headers: Additional headers.
        metadata: Extra configuration data.
    """

    name: str = ""
    api_key: str = ""
    base_url: str = ""
    timeout: float = 30.0
    max_retries: int = 3
    headers: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class HealthCheckResult:
    """Result of an integration health check.

    Attributes:
        healthy: Whether the integration is healthy.
        latency_ms: Health check latency in milliseconds.
        message: Additional info message.
    """

    healthy: bool = True
    latency_ms: float = 0.0
    message: str = ""
