"""AIOS Version Contracts — central version registry for all public interfaces.

Used by contract tests to verify interface stability. Import this module
to check that frozen interfaces haven't changed unexpectedly.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InterfaceVersion:
    """A versioned interface contract."""
    package: str
    module: str
    version: str
    frozen_classes: tuple[str, ...] = ()
    frozen_functions: tuple[str, ...] = ()
    frozen_enums: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Frozen interface registry — add entries here when freezing new interfaces
# ---------------------------------------------------------------------------

FROZEN_INTERFACES: dict[str, InterfaceVersion] = {
    "agents": InterfaceVersion(
        package="aios-agents",
        module="aios.agents",
        version="1.0",
        frozen_classes=(
            "InferenceEngine",
            "BaseAgent",
            "ReActAgent",
            "EventBus",
            "RegistryBase",
            "CapabilityRegistry",
            "PermissionSet",
            "PermissionChecker",
        ),
        frozen_enums=(
            "EventType",
            "Role",
            "StepType",
            "Quantization",
        ),
        frozen_functions=(
            "get_event_bus",
            "reset_event_bus",
        ),
    ),
    "memory": InterfaceVersion(
        package="aios-memory",
        module="aios.memory",
        version="1.0",
        frozen_classes=(
            "MemoryBackend",
            "HybridMemoryManager",
            "BackendConfig",
        ),
        frozen_enums=(
            "MemoryEventType",
        ),
    ),
    "context": InterfaceVersion(
        package="aios-context",
        module="aios.context",
        version="1.0",
        frozen_classes=(
            "ContextBuilder",
            "ContextSummarizer",
            "RelevanceRanker",
            "ConversationWindow",
            "MemoryRetriever",
        ),
        frozen_functions=(
            "inject_context",
        ),
    ),
    "workflows": InterfaceVersion(
        package="aios-workflows",
        module="aios.workflows",
        version="1.0",
        frozen_classes=(
            "Workflow",
            "WorkflowStep",
            "WorkflowResult",
            "WorkflowExecutor",
            "WorkflowPlanner",
            "WorkflowState",
        ),
        frozen_enums=(
            "StepStatus",
            "WorkflowStatus",
        ),
    ),
    "plugins": InterfaceVersion(
        package="aios-plugins",
        module="aios.plugins",
        version="1.0",
        frozen_classes=(
            "PluginManifest",
            "PluginRuntime",
            "PluginSandbox",
            "SandboxConfig",
        ),
        frozen_enums=(
            "PluginStatus",
        ),
    ),
    "sdk": InterfaceVersion(
        package="aios-sdk",
        module="aios.sdk",
        version="1.0",
        frozen_classes=(
            "AiosClient",
        ),
    ),
    "gateway": InterfaceVersion(
        package="aios-gateway",
        module="aios.gateway",
        version="1.0",
        frozen_functions=(
            "run",
        ),
    ),
    "orchestrator": InterfaceVersion(
        package="aios-orchestrator",
        module="aios.orchestrator",
        version="1.0",
        frozen_classes=(
            "Orchestrator",
            "Session",
        ),
    ),
}


def get_version(package: str) -> str:
    """Return the frozen version string for a package."""
    if package not in FROZEN_INTERFACES:
        raise KeyError(f"No frozen interface for '{package}'")
    return FROZEN_INTERFACES[package].version


def list_packages() -> list[str]:
    """Return all packages with frozen interfaces."""
    return sorted(FROZEN_INTERFACES.keys())


def check_all_versions() -> dict[str, str]:
    """Return {package: version} for all frozen interfaces."""
    return {k: v.version for k, v in FROZEN_INTERFACES.items()}
