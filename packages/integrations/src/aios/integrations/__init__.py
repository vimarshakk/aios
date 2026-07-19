"""AIOS Integrations Platform.

Third-party service integration framework with registry, auth, and lifecycle management.
"""

from __future__ import annotations

from aios.integrations.base import Integration, IntegrationConfig, IntegrationStatus
from aios.integrations.connector import (
    Connector,
    ConnectorBinding,
    ConnectorRegistry,
    ConnectorRoute,
)
from aios.integrations.registry import IntegrationRegistry
from aios.integrations.types import IntegrationResult

API_VERSION = "1.0"

__all__ = [
    "API_VERSION",
    "Connector",
    "ConnectorBinding",
    "ConnectorRegistry",
    "ConnectorRoute",
    "Integration",
    "IntegrationConfig",
    "IntegrationRegistry",
    "IntegrationResult",
    "IntegrationStatus",
]
