"""Plugin loader — reads a plugin directory and returns a PluginManifest + module."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from aios.plugins.manifest import PluginManifest

if TYPE_CHECKING:
    from types import ModuleType


@dataclass
class LoadedPlugin:
    """A loaded plugin — manifest + live module reference.

    Attributes:
        manifest: The parsed manifest.
        module: The imported plugin module (or None for manifest-only plugins).
        path: Filesystem path to the plugin directory.
    """

    manifest: PluginManifest
    module: ModuleType | None
    path: Path


class PluginLoadError(Exception):
    """Raised when a plugin cannot be loaded."""


def load_plugin(directory: str | Path) -> LoadedPlugin:
    """Load a plugin from a directory containing ``plugin.yaml``.

    Steps:
        1. Read and parse ``plugin.yaml``.
        2. If an ``entry_point`` is specified, import the Python module.
        3. Return a ``LoadedPlugin`` combining manifest + module.

    Raises:
        PluginLoadError: On missing manifest, parse errors, or import failures.
    """
    plugin_dir = Path(directory)
    manifest_path = plugin_dir / "plugin.yaml"
    if not manifest_path.exists():
        raise PluginLoadError(f"No plugin.yaml found in {plugin_dir}")

    try:
        manifest = PluginManifest.from_file(manifest_path)
    except Exception as exc:
        raise PluginLoadError(f"Failed to parse manifest: {exc}") from exc

    module: ModuleType | None = None
    if manifest.entry_point:
        module = _import_entry_point(manifest.entry_point, plugin_dir)

    return LoadedPlugin(manifest=manifest, module=module, path=plugin_dir)


def load_plugin_from_zip(zip_path: str | Path) -> LoadedPlugin:
    """Load a plugin from a zip archive (future use).

    Currently raises NotImplementedError — use directory loading for M1.
    """
    raise NotImplementedError("Zip-based plugin loading is planned for M2")


def _import_entry_point(dotted_path: str, plugin_dir: Path) -> ModuleType:
    """Import a Python module from a dotted path, adding the plugin dir to sys.path."""
    parts = dotted_path.split(".")
    module_name = parts[-1]

    # Add parent dir to sys.path temporarily
    dir_str = str(plugin_dir)
    path_added = dir_str not in sys.path
    if path_added:
        sys.path.insert(0, dir_str)

    try:
        spec = importlib.util.find_spec(module_name)
    except Exception as exc:
        raise PluginLoadError(
            f"Failed to import '{dotted_path}': {exc}"
        ) from exc
    else:
        if spec is None or spec.origin is None:
            raise PluginLoadError(
                f"Cannot find module '{module_name}' in {plugin_dir}"
            )
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module
    finally:
        if path_added and dir_str in sys.path:
            sys.path.remove(dir_str)
