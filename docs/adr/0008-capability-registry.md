# ADR-0008: Capability Registry — Typed Discovery System

**Status:** Accepted  
**Date:** 2026-07-17  
**Deciders:** AIOS Core Team

## Problem

AIOS needs a unified way to discover and retrieve agents, tools, skills, providers, plugins, prompts, and workflows. A flat string-keyed registry is insufficient for typed lookups and capability-based search.

## Decision

Implement a generic `RegistryBase[T]` with typed subclasses and a `CapabilityRegistry` facade:

- 12 typed registries: `AgentRegistry`, `ToolRegistry`, `SkillRegistry`, `ProviderRegistry`, `PluginRegistry`, `PromptRegistry`, `WorkflowRegistry`, `ModelRegistry`, `EngineRegistry`, `MemoryRegistry`, `FactStoreRegistry`, `ConnectorRegistry`
- `Capability` frozen dataclass with `name`, `capability_type`, `version`, `description`, `permissions`, `tags`
- `CapabilityRegistry` facade: `register()`, `discover()`, `find(query, capability_type, tag)`, `get()`, `get_entry()`

```python
class RegistryBase[T]:
    @classmethod register(key: str) -> Callable[[T], T]: ...  # decorator
    @classmethod get(key: str) -> T: ...
    @classmethod items() -> tuple[tuple[str, T], ...]: ...

class CapabilityRegistry:
    @classmethod register(name, capability_type, entry_point, *, version, description, permissions, tags) -> Capability: ...
    @classmethod discover() -> list[Capability]: ...
    @classmethod find(query="", *, capability_type, tag) -> list[Capability]: ...
```

## Rationale

- **Generic base:** `RegistryBase[T]` eliminates boilerplate. Each typed registry inherits `register`, `get`, `items`, `keys`, `contains`, `clear`.
- **Decorator pattern:** `@AgentRegistry.register("name")` is idiomatic Python and self-documenting.
- **Facade for cross-cutting queries:** `CapabilityRegistry.find(query="browser")` searches across all registry types.
- **Capability metadata:** `version`, `permissions`, `tags` enable capability negotiation and filtering.

## Alternatives Considered

1. **Single monolithic registry:** Rejected — loses type safety. `AgentRegistry.get("x")` returns `BaseAgent`, not `Any`.
2. **Dict-based registries (no base class):** Rejected — duplicate code across 12 registries.
3. **External service registry (Consul/etcd):** Over-engineered for M1. In-process class-level storage is sufficient.

## Consequences

- All registries use class-level storage (class variables). Clearing one registry doesn't affect others.
- `CapabilityRegistry.clear()` only clears metadata, not the underlying typed registries.
- `Capability.entry_point` is `Any` — typed to the specific registry in practice.
- `items()` returns `tuple` (immutable snapshot) to prevent mutation during iteration.

## Future Evolution

- M2: Capability graph (structured hierarchy instead of flat tags).
- M2: Registry persistence (save/load to disk or database).
- M3: Distributed registry (cross-instance capability discovery).
