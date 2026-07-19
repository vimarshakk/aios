# ADR-0006: Plugin Runtime — Dynamic Extension System

**Status:** Accepted  
**Date:** 2026-07-17  
**Deciders:** AIOS Core Team

## Problem

AIOS needs a way for third parties to extend the system (add tools, skills, workflows) without modifying core code. The extension mechanism must be safe, discoverable, and lifecycle-managed.

## Decision

Implement a plugin system with:
- `PluginManifest` (YAML-based, frozen dataclass) describing tools, permissions, events, skills
- `PluginRuntime` (install/enable/disable/uninstall lifecycle)
- `PluginLoader` (directory-based discovery, dynamic Python import)
- `PluginSandbox` (advisory permission checking for M1)

```python
class PluginManifest:
    name: str; version: str; tools: tuple[ToolSpec, ...]; permissions: tuple[str, ...]
    @classmethod from_yaml(text: str) -> PluginManifest: ...
    @classmethod from_file(path: Path) -> PluginManifest: ...

class PluginRuntime:
    def install(directory: Path) -> Plugin: ...
    def enable(name: str) -> None: ...
    def disable(name: str) -> None: ...
    def get_tools(name: str) -> list[dict]: ...
```

## Rationale

- **YAML manifests:** Human-readable, diffable, no code execution for metadata.
- **Frozen dataclasses:** Immutability prevents runtime manifest corruption.
- **Lifecycle management:** Install → enable → disable → uninstall with status tracking.
- **Sandbox (advisory):** Permission checking without OS-level isolation for M1. Real sandboxing (containers, seccomp) in M2.

## Alternatives Considered

1. **Entry points (setuptools):** Rejected — requires package installation, not suitable for runtime-loaded plugins.
2. **JSON manifests:** Rejected — YAML is more readable for multi-line descriptions and tool specs.
3. **Full sandbox from day 1:** Deferred — OS-level isolation adds significant complexity. Advisory sandbox is sufficient for trusted plugins.

## Consequences

- Plugins declare permissions via manifest. `PluginSandbox` records violations but does not block in M1.
- `LoadedPlugin` carries both manifest and imported module for runtime use.
- `PluginRuntime` is in-memory only — no disk persistence of install state in M1.
- Entry point loading uses `importlib` with `sys.path` management for plugin directories.

## Future Evolution

- M2: Persistent plugin state (installed plugins survive restarts).
- M2: OS-level sandbox (containers, seccomp, AppArmor).
- M2: Plugin marketplace / registry API.
- M3: Plugin hot-reload without restart.
