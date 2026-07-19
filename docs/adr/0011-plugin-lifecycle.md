# ADR-0011: Plugin Lifecycle Management

**Date:** 2025-07-17
**Status:** Accepted
**Deciders:** Core team

## Context

M1 introduced plugin manifests but had no lifecycle management. Plugins could be installed but not started, stopped, or health-checked. M2 added a full lifecycle manager with start/stop/restart, dependency resolution, and health monitoring.

## Decision

Implement a `PluginLifecycleManager` that manages the full plugin lifecycle:

- **States:** `pending → installed → starting → running → stopping → stopped → error → disabled`
- **Dependency resolution:** Topological sort with cycle detection
- **Health checks:** Periodic async health checks via plugin `health()` method
- **Start/stop/restart:** Graceful shutdown with configurable timeout
- **Error handling:** Failed plugins don't block others; errors captured with timestamps

## Consequences

- Plugins must implement `health() → PluginHealth` for monitoring
- Dependencies are validated at install time (missing deps raise errors)
- Start order respects dependencies (topological sort)
- The lifecycle manager is a plain class, not a service — no DI overhead
- Health checks run in the event loop; plugins must be async-safe

## Alternatives Considered

1. **State machine per plugin:** More formal but overkill for current needs
2. **External process per plugin:** Better isolation but adds complexity
3. **Use existing event bus for lifecycle events:** Possible but creates circular dependency

## References

- `packages/plugin-sdk/src/aios/plugin_sdk/lifecycle.py`
- `tests/test_plugin_lifecycle.py`
