"""Plugin runtime — install, enable, disable, uninstall plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from aios.plugins.loader import LoadedPlugin, load_plugin

if TYPE_CHECKING:
    from aios.plugins.manifest import PluginManifest


class PluginStatus(StrEnum):
    """Lifecycle state of a plugin."""

    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class Plugin:
    """A managed plugin instance.

    Attributes:
        manifest: The parsed plugin manifest.
        status: Current lifecycle status.
        path: Filesystem path to the plugin directory.
        error: Error message if the plugin is in ERROR state.
    """

    manifest: PluginManifest
    status: PluginStatus = PluginStatus.INSTALLED
    path: Path = field(default_factory=Path)
    error: str = ""


class PluginNotFoundError(Exception):
    """Raised when referencing a plugin that is not installed."""


class PluginAlreadyInstalledError(Exception):
    """Raised when trying to install a plugin that is already installed."""


class PluginRuntime:
    """Manage the full lifecycle of plugins.

    Plugins are identified by their manifest name.  The runtime tracks
    installed, enabled, and disabled plugins in memory.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    # -- queries -----------------------------------------------------------

    def list_installed(self) -> list[Plugin]:
        """Return all installed plugins."""
        return list(self._plugins.values())

    def get(self, name: str) -> Plugin:
        """Get a plugin by name.  Raises if not found."""
        if name not in self._plugins:
            raise PluginNotFoundError(f"Plugin '{name}' is not installed")
        return self._plugins[name]

    def get_tools(self, name: str) -> list[dict[str, object]]:
        """Return tool specs for a named plugin."""
        plugin = self.get(name)
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in plugin.manifest.tools
        ]

    def is_installed(self, name: str) -> bool:
        return name in self._plugins

    # -- mutations ---------------------------------------------------------

    def install(self, directory: str | Path) -> Plugin:
        """Load and register a plugin from a directory.

        Raises:
            PluginAlreadyInstalledError: If a plugin with the same name exists.
            PluginLoadError: If the directory cannot be loaded.
        """
        loaded: LoadedPlugin = load_plugin(directory)
        name = loaded.manifest.name
        if name in self._plugins:
            raise PluginAlreadyInstalledError(
                f"Plugin '{name}' is already installed"
            )

        plugin = Plugin(
            manifest=loaded.manifest,
            status=PluginStatus.ENABLED if loaded.manifest.enabled else PluginStatus.DISABLED,
            path=loaded.path,
        )
        self._plugins[name] = plugin
        return plugin

    def enable(self, name: str) -> None:
        """Enable an installed plugin."""
        plugin = self.get(name)
        plugin.status = PluginStatus.ENABLED

    def disable(self, name: str) -> None:
        """Disable an installed plugin."""
        plugin = self.get(name)
        plugin.status = PluginStatus.DISABLED

    def uninstall(self, name: str) -> None:
        """Remove a plugin from the registry.

        Does NOT delete files on disk — that is the caller's responsibility.
        """
        if name not in self._plugins:
            raise PluginNotFoundError(f"Plugin '{name}' is not installed")
        del self._plugins[name]

    def mark_error(self, name: str, error: str) -> None:
        """Mark a plugin as errored."""
        plugin = self.get(name)
        plugin.status = PluginStatus.ERROR
        plugin.error = error
