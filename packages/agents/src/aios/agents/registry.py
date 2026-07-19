"""Decorator-based registry for runtime discovery of pluggable components.

Extracted from OpenJarvis core/registry.py (Apache 2.0).
Each typed subclass gets isolated storage so registrations never leak.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# ---------------------------------------------------------------------------
# Capability metadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Capability:
    """Metadata for a discovered AIOS capability.

    Attributes:
        name: Unique identifier within its type namespace.
        capability_type: One of agent, tool, skill, provider, plugin, prompt, workflow.
        version: Semver string (e.g. "1.0.0").
        description: Human-readable summary.
        permissions: Permission strings required by this capability.
        tags: Freeform tags for search/filtering.
        entry_point: The registered object (class, function, or manifest dict).
    """

    name: str
    capability_type: str
    version: str = "0.0.0"
    description: str = ""
    permissions: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    entry_point: Any = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# RegistryBase
# ---------------------------------------------------------------------------


class RegistryBase[T]:
    """Generic registry base class with class-specific entry isolation."""

    @classmethod
    def _entries(cls) -> dict[str, T]:
        attr_name = f"_registry_entries_{cls.__name__}"
        storage = getattr(cls, attr_name, None)
        if storage is None:
            storage = {}
            setattr(cls, attr_name, storage)
        return storage

    @classmethod
    def register(cls, key: str) -> Callable[[T], T]:
        def decorator(entry: T) -> T:
            entries = cls._entries()
            if key in entries:
                raise ValueError(f"{cls.__name__} already has an entry for '{key}'")
            entries[key] = entry
            return entry
        return decorator

    @classmethod
    def register_value(cls, key: str, value: T) -> T:
        entries = cls._entries()
        if key in entries:
            raise ValueError(f"{cls.__name__} already has an entry for '{key}'")
        entries[key] = value
        return value

    @classmethod
    def get(cls, key: str) -> T:
        try:
            return cls._entries()[key]
        except KeyError as exc:
            raise KeyError(
                f"{cls.__name__} does not have an entry for '{key}'"
            ) from exc

    @classmethod
    def create(cls, key: str, *args: Any, **kwargs: Any) -> Any:
        entry = cls.get(key)
        if not callable(entry):
            raise TypeError(
                f"{cls.__name__} entry '{key}' is not callable"
            )
        return entry(*args, **kwargs)

    @classmethod
    def items(cls) -> tuple[tuple[str, T], ...]:
        return tuple(cls._entries().items())

    @classmethod
    def keys(cls) -> tuple[str, ...]:
        return tuple(cls._entries().keys())

    @classmethod
    def contains(cls, key: str) -> bool:
        return key in cls._entries()

    @classmethod
    def clear(cls) -> None:
        cls._entries().clear()


# ---------------------------------------------------------------------------
# Typed subclass registries — one per primitive
# ---------------------------------------------------------------------------


class ModelRegistry(RegistryBase[Any]):
    """Registry for ModelSpec objects."""


class EngineRegistry(RegistryBase[Any]):
    """Registry for inference engine backends."""


class MemoryRegistry(RegistryBase[Any]):
    """Registry for memory / retrieval backends."""


class FactStoreRegistry(RegistryBase[Any]):
    """Registry for automatic-memory fact store backends."""


class AgentRegistry(RegistryBase[Any]):
    """Registry for agent implementations."""


class ToolRegistry(RegistryBase[Any]):
    """Registry for tool specifications."""


class SkillRegistry(RegistryBase[Any]):
    """Registry for skill manifests."""


class ConnectorRegistry(RegistryBase[Any]):
    """Registry for data source connectors (Gmail, Slack, etc.)."""


class PluginRegistry(RegistryBase[Any]):
    """Registry for plugin manifests and instances."""


class PromptRegistry(RegistryBase[Any]):
    """Registry for prompt templates."""


class WorkflowRegistry(RegistryBase[Any]):
    """Registry for workflow definitions."""


class ProviderRegistry(RegistryBase[Any]):
    """Registry for inference provider backends."""


# ---------------------------------------------------------------------------
# CapabilityRegistry — unified discovery facade
# ---------------------------------------------------------------------------

# Maps a Capability type name to the corresponding RegistryBase subclass.
_TYPE_REGISTRY_MAP: dict[str, type[RegistryBase[Any]]] = {
    "agent": AgentRegistry,
    "tool": ToolRegistry,
    "skill": SkillRegistry,
    "provider": ProviderRegistry,
    "plugin": PluginRegistry,
    "prompt": PromptRegistry,
    "workflow": WorkflowRegistry,
}

_CAPABILITY_TYPE_NAMES = frozenset(_TYPE_REGISTRY_MAP.keys())


class CapabilityRegistry:
    """Unified facade over all typed registries with search and discovery.

    Capabilities are registered per-type.  The facade aggregates across
    all types for ``discover`` and ``find`` queries.
    """

    @classmethod
    def register(
        cls,
        name: str,
        capability_type: str,
        entry_point: Any = None,
        *,
        version: str = "0.0.0",
        description: str = "",
        permissions: tuple[str, ...] | list[str] = (),
        tags: tuple[str, ...] | list[str] = (),
    ) -> Capability:
        """Register a capability in the appropriate typed registry and return its metadata."""
        if capability_type not in _CAPABILITY_TYPE_NAMES:
            raise ValueError(
                f"Unknown capability type '{capability_type}'. "
                f"Valid types: {sorted(_CAPABILITY_TYPE_NAMES)}"
            )

        reg_cls = _TYPE_REGISTRY_MAP[capability_type]
        reg_cls.register_value(name, entry_point)

        cap = Capability(
            name=name,
            capability_type=capability_type,
            version=version,
            description=description,
            permissions=tuple(permissions),
            tags=tuple(tags),
            entry_point=entry_point,
        )
        # Store capability metadata alongside the raw entry
        cls._capabilities()[name] = cap
        return cap

    @classmethod
    def discover(cls) -> list[Capability]:
        """List all registered capabilities across all types."""
        return list(cls._capabilities().values())

    @classmethod
    def find(
        cls,
        query: str = "",
        *,
        capability_type: str | None = None,
        tag: str | None = None,
    ) -> list[Capability]:
        """Search capabilities by name/description/tags.

        Args:
            query: Substring match against name and description (case-insensitive).
            capability_type: Filter to a single capability type.
            tag: Filter to capabilities that include this tag.

        Returns:
            Matching capabilities sorted by name.
        """
        q = query.lower()
        results: list[Capability] = []
        for cap in cls._capabilities().values():
            if capability_type is not None and cap.capability_type != capability_type:
                continue
            if tag is not None and tag not in cap.tags:
                continue
            if q and q not in cap.name.lower() and q not in cap.description.lower():
                continue
            results.append(cap)
        results.sort(key=lambda c: c.name)
        return results

    @classmethod
    def get(cls, name: str) -> Capability:
        """Get a specific capability by name."""
        caps = cls._capabilities()
        if name not in caps:
            raise KeyError(f"No capability registered with name '{name}'")
        return caps[name]

    @classmethod
    def get_entry(cls, name: str) -> Any:
        """Get the entry_point object for a named capability."""
        return cls.get(name).entry_point

    @classmethod
    def clear(cls) -> None:
        """Remove all capability metadata.  Does NOT clear typed registries."""
        cls._capabilities().clear()

    # -- private -----------------------------------------------------------

    @classmethod
    def _capabilities(cls) -> dict[str, Capability]:
        attr = "_capability_entries"
        storage = getattr(cls, attr, None)
        if storage is None:
            storage = {}
            setattr(cls, attr, storage)
        return storage


__all__ = [
    "AgentRegistry",
    "Capability",
    "CapabilityRegistry",
    "ConnectorRegistry",
    "EngineRegistry",
    "FactStoreRegistry",
    "MemoryRegistry",
    "ModelRegistry",
    "PluginRegistry",
    "PromptRegistry",
    "ProviderRegistry",
    "RegistryBase",
    "SkillRegistry",
    "ToolRegistry",
    "WorkflowRegistry",
]
