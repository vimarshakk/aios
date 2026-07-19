"""AIOS Plugins — Dynamic plugin installation, lifecycle, manifest parsing, and marketplace."""

from __future__ import annotations

from aios.plugins.dependencies import (
    CircularDependencyError,
    DependencyError,
    DependencyResolver,
    MissingDependencyError,
    ResolvedDependency,
)
from aios.plugins.manifest import PluginManifest, ToolSpec
from aios.plugins.marketplace import (
    MarketplaceEntry,
    MarketplaceNotFoundError,
    PluginMarketplace,
    VersionConflictError,
)
from aios.plugins.runtime import (
    Plugin,
    PluginAlreadyInstalledError,
    PluginNotFoundError,
    PluginRuntime,
    PluginStatus,
)
from aios.plugins.sandbox import (
    PermissionPolicy,
    PluginSandbox,
    SandboxConfig,
    SandboxResult,
)
from aios.plugins.versions import SemVer, VersionRange, is_compatible

API_VERSION = "1.0"

__all__ = [
    "CircularDependencyError",
    "DependencyError",
    "DependencyResolver",
    "LoadedPlugin",
    "MarketplaceEntry",
    "MarketplaceNotFoundError",
    "MissingDependencyError",
    "PermissionPolicy",
    "Plugin",
    "PluginAlreadyInstalledError",
    "PluginLoadError",
    "PluginManifest",
    "PluginMarketplace",
    "PluginNotFoundError",
    "PluginRuntime",
    "PluginSandbox",
    "PluginStatus",
    "ResolvedDependency",
    "SandboxConfig",
    "SandboxResult",
    "SemVer",
    "ToolSpec",
    "VersionConflictError",
    "VersionRange",
    "is_compatible",
    "load_plugin",
]
