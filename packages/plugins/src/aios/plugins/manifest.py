"""Plugin manifest — structured metadata for a plugin."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Description of a single tool exposed by a plugin."""

    name: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Parsed content of a ``plugin.yaml`` manifest.

    Attributes:
        name: Unique plugin identifier (e.g. ``github``).
        version: Semver string.
        description: Human-readable summary.
        author: Plugin author.
        permissions: Permission strings required by the plugin.
        tools: Tool specifications exposed by the plugin.
        events: Event type names the plugin subscribes to.
        skills: Skill names the plugin provides.
        entry_point: Python dotted path to the plugin's main class/module.
        enabled: Whether the plugin is enabled after install.
    """

    name: str
    version: str = "0.0.0"
    description: str = ""
    author: str = ""
    permissions: tuple[str, ...] = ()
    tools: tuple[ToolSpec, ...] = ()
    events: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    entry_point: str = ""
    enabled: bool = True

    # -- parsing -----------------------------------------------------------

    @classmethod
    def from_yaml(cls, text: str) -> PluginManifest:
        """Parse a YAML string into a PluginManifest."""
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise ValueError("Plugin manifest must be a YAML mapping")

        tools_raw = data.get("tools", [])
        tools = tuple(
            ToolSpec(
                name=t["name"],
                description=t.get("description", ""),
                parameters=t.get("parameters", {}),
            )
            for t in tools_raw
            if isinstance(t, dict) and "name" in t
        )

        return cls(
            name=data["name"],
            version=data.get("version", "0.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            permissions=tuple(data.get("permissions", [])),
            tools=tools,
            events=tuple(data.get("events", [])),
            skills=tuple(data.get("skills", [])),
            entry_point=data.get("entry_point", ""),
            enabled=data.get("enabled", True),
        )

    @classmethod
    def from_file(cls, path: str | Path) -> PluginManifest:
        """Read and parse a ``plugin.yaml`` file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Manifest not found: {p}")
        return cls.from_yaml(p.read_text(encoding="utf-8"))
