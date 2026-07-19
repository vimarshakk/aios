"""OSS Integration Adapters — wrap upstream open-source projects behind AIOS adapters.

Architecture:
    AIOS Interface → Adapter → Upstream Project

Each adapter:
- Subclasses Integration (lifecycle: connect/disconnect/execute)
- Wraps an upstream OSS project behind AIOS capabilities
- Reports availability at runtime (upstream packages are optional)
- Preserves upstream license and attribution
- Remains independently updatable

Adapters:
- OpenJarvis: workflow engine, scheduler, evaluations, reasoning
- OpenHands: coding agent, sandbox, git, browser-assisted coding
- OpenInterpreter: desktop agent, shell/python execution, file ops
- AnythingLLM: document ingestion, embeddings, RAG, retrieval
- LibreChat: conversation management, artifacts, session management
- OpenWebUI: local model management, provider config, inference
- Continue: IDE support, codebase indexing, autocomplete, MCP
- Jan: model downloads, lifecycle management, versioning
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aios.integrations.oss.anythingllm import AnythingLLMIntegration
from aios.integrations.oss.connectors import (
    AnythingLLMConnector,
    ContinueConnector,
    JanConnector,
    LibreChatConnector,
    OpenHandsConnector,
    OpenInterpreterConnector,
    OpenJarvisConnector,
    OpenWebUIConnector,
)
from aios.integrations.oss.continue_dev import ContinueIntegration
from aios.integrations.oss.jan import JanIntegration
from aios.integrations.oss.librechat import LibreChatIntegration
from aios.integrations.oss.openhands import OpenHandsIntegration
from aios.integrations.oss.openinterpreter import OpenInterpreterIntegration
from aios.integrations.oss.openjarvis import OpenJarvisIntegration
from aios.integrations.oss.openwebui import OpenWebUIIntegration

if TYPE_CHECKING:
    from aios.integrations.base import Integration
    from aios.integrations.connector import Connector
    from aios.integrations.types import IntegrationConfig

API_VERSION = "1.0"

# Upstream version registry — populated at import time
UPSTREAM_VERSIONS: dict[str, str | None] = {
    "openjarvis": OpenJarvisIntegration().upstream_version,
    "openhands": OpenHandsIntegration().upstream_version,
    "openinterpreter": OpenInterpreterIntegration().upstream_version,
    "anythingllm": AnythingLLMIntegration().upstream_version,
    "librechat": LibreChatIntegration().upstream_version,
    "openwebui": OpenWebUIIntegration().upstream_version,
    "continue": ContinueIntegration().upstream_version,
    "jan": JanIntegration().upstream_version,
}

# Upstream licenses
UPSTREAM_LICENSES: dict[str, str] = {
    "openjarvis": "MIT",
    "openhands": "MIT",
    "openinterpreter": "MIT",
    "anythingllm": "MIT",
    "librechat": "MIT",
    "openwebui": "BSD-2-Clause",
    "continue": "Apache-2.0",
    "jan": "AGPL-3.0",
}

# Adapter registry — maps name → (Integration class, Connector class)
ADAPTER_REGISTRY: dict[str, tuple[type[Integration], type[Connector]]] = {
    "openjarvis": (OpenJarvisIntegration, OpenJarvisConnector),
    "openhands": (OpenHandsIntegration, OpenHandsConnector),
    "openinterpreter": (OpenInterpreterIntegration, OpenInterpreterConnector),
    "anythingllm": (AnythingLLMIntegration, AnythingLLMConnector),
    "librechat": (LibreChatIntegration, LibreChatConnector),
    "openwebui": (OpenWebUIIntegration, OpenWebUIConnector),
    "continue": (ContinueIntegration, ContinueConnector),
    "jan": (JanIntegration, JanConnector),
}


def create_oss_integration(
    name: str, config: IntegrationConfig | None = None
) -> Integration:
    """Factory: create an OSS integration by name.

    Args:
        name: Adapter name (e.g. "openjarvis", "openhands").
        config: Optional configuration.

    Returns:
        Integration instance.

    Raises:
        ValueError: If name is not a known OSS adapter.
    """
    if name not in ADAPTER_REGISTRY:
        raise ValueError(
            f"Unknown OSS adapter: {name}. "
            f"Available: {', '.join(sorted(ADAPTER_REGISTRY))}"
        )
    cls, _ = ADAPTER_REGISTRY[name]
    return cls(config)


def create_oss_connector(
    name: str, integration: Integration
) -> Connector:
    """Factory: create an OSS connector by name, backed by the given integration.

    Args:
        name: Adapter name (e.g. "openjarvis", "openhands").
        integration: Backing integration instance.

    Returns:
        Connector instance.

    Raises:
        ValueError: If name is not a known OSS adapter.
    """
    if name not in ADAPTER_REGISTRY:
        raise ValueError(
            f"Unknown OSS adapter: {name}. "
            f"Available: {', '.join(sorted(ADAPTER_REGISTRY))}"
        )
    _, cls = ADAPTER_REGISTRY[name]
    return cls(integration)


def register_all_oss(
    integration_registry: object,
    connector_registry: object,
    config_factory: object | None = None,
) -> dict[str, dict[str, bool]]:
    """Register all OSS adapters into both registries.

    Args:
        integration_registry: IntegrationRegistry instance.
        connector_registry: ConnectorRegistry instance.
        config_factory: Optional callable(name) -> IntegrationConfig.

    Returns:
        Dict mapping adapter names to {available: bool, registered: bool}.
    """
    from aios.integrations.registry import IntegrationRegistry  # noqa: F811
    from aios.integrations.connector import ConnectorRegistry  # noqa: F811

    results: dict[str, dict[str, bool]] = {}
    for name, (int_cls, conn_cls) in ADAPTER_REGISTRY.items():
        cfg = config_factory(name) if config_factory else None
        integration = int_cls(cfg)
        connector = conn_cls(integration)

        available = integration.is_available
        try:
            integration_registry.register(integration)  # type: ignore[union-attr]
            registered_int = True
        except ValueError:
            registered_int = False

        try:
            connector_registry.register(connector)  # type: ignore[union-attr]
            registered_conn = True
        except ValueError:
            registered_conn = False

        results[name] = {
            "available": available,
            "integration_registered": registered_int,
            "connector_registered": registered_conn,
        }
    return results


__all__ = [
    "API_VERSION",
    "UPSTREAM_VERSIONS",
    "UPSTREAM_LICENSES",
    "ADAPTER_REGISTRY",
    "AnythingLLMConnector",
    "AnythingLLMIntegration",
    "ContinueConnector",
    "ContinueIntegration",
    "JanConnector",
    "JanIntegration",
    "LibreChatConnector",
    "LibreChatIntegration",
    "OpenHandsConnector",
    "OpenHandsIntegration",
    "OpenInterpreterConnector",
    "OpenInterpreterIntegration",
    "OpenJarvisConnector",
    "OpenJarvisIntegration",
    "OpenWebUIConnector",
    "OpenWebUIIntegration",
    "create_oss_integration",
    "create_oss_connector",
    "register_all_oss",
]
