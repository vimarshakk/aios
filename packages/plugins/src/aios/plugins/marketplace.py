"""Plugin marketplace — registry of available plugins with install/uninstall."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from aios.plugins.manifest import PluginManifest, ToolSpec
from aios.plugins.versions import SemVer


@dataclass(frozen=True, slots=True)
class MarketplaceEntry:
    """A plugin entry in the marketplace registry.

    Attributes:
        name: Unique plugin identifier.
        version: Current version string.
        description: Human-readable summary.
        author: Plugin author.
        permissions: Permission strings required.
        tools: Tool specifications exposed.
        events: Event names subscribed to.
        skills: Skill names provided.
        entry_point: Python dotted path to main module.
        dependencies: Required plugins as {name: version_range}.
        tags: Searchable tags.
        downloads: Download/install count.
        published_at: Unix timestamp of publication.
        updated_at: Unix timestamp of last update.
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
    dependencies: dict[str, str] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    downloads: int = 0
    published_at: float = 0.0
    updated_at: float = 0.0

    # -- conversion --------------------------------------------------------

    @classmethod
    def from_manifest(cls, manifest: PluginManifest) -> MarketplaceEntry:
        """Create a marketplace entry from a plugin manifest."""
        now = time.time()
        return cls(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            author=manifest.author,
            permissions=manifest.permissions,
            tools=manifest.tools,
            events=manifest.events,
            skills=manifest.skills,
            entry_point=manifest.entry_point,
            published_at=now,
            updated_at=now,
        )

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        d = asdict(self)
        d["tools"] = [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            }
            for t in self.tools
        ]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> MarketplaceEntry:
        """Deserialize from a dict."""
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
            dependencies=data.get("dependencies", {}),
            tags=tuple(data.get("tags", [])),
            downloads=data.get("downloads", 0),
            published_at=data.get("published_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
        )


class MarketplaceNotFoundError(Exception):
    """Raised when referencing a plugin that doesn't exist in the marketplace."""


class VersionConflictError(Exception):
    """Raised when a version constraint cannot be satisfied."""


def _bump_downloads(entry: MarketplaceEntry) -> MarketplaceEntry:
    """Return a new entry with downloads incremented."""
    return MarketplaceEntry(
        name=entry.name,
        version=entry.version,
        description=entry.description,
        author=entry.author,
        permissions=entry.permissions,
        tools=entry.tools,
        events=entry.events,
        skills=entry.skills,
        entry_point=entry.entry_point,
        dependencies=entry.dependencies,
        tags=entry.tags,
        downloads=entry.downloads + 1,
        published_at=entry.published_at,
        updated_at=entry.updated_at,
    )


class PluginMarketplace:
    """In-memory + JSONL-backed registry of marketplace plugins.

    Provides publish, search, install, uninstall, and version management.
    """

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self._entries: dict[str, MarketplaceEntry] = {}
        self._installed: dict[str, str] = {}  # name → installed version
        self._storage_path = Path(storage_path) if storage_path else None
        if self._storage_path and self._storage_path.exists():
            self._load()

    # -- persistence -------------------------------------------------------

    def _load(self) -> None:
        """Load entries from the JSONL storage file."""
        if not self._storage_path or not self._storage_path.exists():
            return
        with self._storage_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                entry = MarketplaceEntry.from_dict(data)
                self._entries[entry.name] = entry

    def _save(self) -> None:
        """Persist all entries to the JSONL storage file."""
        if not self._storage_path:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self._storage_path.open("w", encoding="utf-8") as f:
            for entry in self._entries.values():
                f.write(json.dumps(entry.to_dict()) + "\n")

    # -- registry operations -----------------------------------------------

    def publish(self, entry: MarketplaceEntry) -> MarketplaceEntry:
        """Add or update an entry in the marketplace."""
        existing = self._entries.get(entry.name)
        if existing:
            existing_ver = SemVer.parse(existing.version)
            new_ver = SemVer.parse(entry.version)
            if new_ver <= existing_ver:
                raise VersionConflictError(
                    f"Version {entry.version} is not greater than "
                    f"existing {existing.version} for '{entry.name}'"
                )
        self._entries[entry.name] = entry
        self._save()
        return entry

    def get(self, name: str) -> MarketplaceEntry:
        """Get an entry by name."""
        if name not in self._entries:
            raise MarketplaceNotFoundError(
                f"Plugin '{name}' not found in marketplace"
            )
        return self._entries[name]

    def search(
        self,
        query: str = "",
        tags: tuple[str, ...] = (),
    ) -> list[MarketplaceEntry]:
        """Search marketplace entries by query text and/or tags."""
        results: list[MarketplaceEntry] = []
        query_lower = query.lower()
        for entry in self._entries.values():
            name_match = query_lower in entry.name.lower()
            desc_match = query_lower in entry.description.lower()
            if query_lower and not name_match and not desc_match:
                continue
            if tags and not any(t in entry.tags for t in tags):
                continue
            results.append(entry)
        return sorted(results, key=lambda e: (-e.downloads, e.name))

    def list_all(self) -> list[MarketplaceEntry]:
        """Return all entries sorted by downloads descending."""
        return sorted(
            self._entries.values(), key=lambda e: (-e.downloads, e.name)
        )

    def remove(self, name: str) -> None:
        """Remove an entry from the marketplace."""
        if name not in self._entries:
            raise MarketplaceNotFoundError(
                f"Plugin '{name}' not found in marketplace"
            )
        del self._entries[name]
        self._save()

    def get_versions(self, name: str) -> list[str]:
        """Get all published versions of a plugin.

        In this single-entry-per-name model, returns the current version.
        """
        entry = self.get(name)
        return [entry.version]

    def check_update(self, name: str, installed_version: str) -> str | None:
        """Check if an update is available for an installed plugin.

        Returns the new version string if available, None otherwise.
        """
        entry = self._entries.get(name)
        if not entry:
            return None
        installed = SemVer.parse(installed_version)
        available = SemVer.parse(entry.version)
        if available > installed:
            return entry.version
        return None

    # -- install/uninstall (marketplace-level) ----------------------------

    def install(self, name: str) -> MarketplaceEntry:
        """Mark a plugin as installed from the marketplace.

        Returns the entry that was installed (with download count bumped).
        """
        entry = self.get(name)
        self._installed[name] = entry.version
        updated = _bump_downloads(entry)
        self._entries[name] = updated
        self._save()
        return updated

    def uninstall(self, name: str) -> None:
        """Mark a plugin as uninstalled from the marketplace."""
        if name not in self._installed:
            raise MarketplaceNotFoundError(
                f"Plugin '{name}' is not installed"
            )
        del self._installed[name]

    def is_installed(self, name: str) -> bool:
        """Check if a plugin is currently installed."""
        return name in self._installed

    def installed_version(self, name: str) -> str | None:
        """Return the installed version of a plugin, or None."""
        return self._installed.get(name)

    def list_installed(self) -> list[MarketplaceEntry]:
        """Return all entries that are currently installed."""
        return [
            self._entries[n] for n in self._installed if n in self._entries
        ]
