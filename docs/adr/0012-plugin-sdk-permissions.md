# ADR-0012: Plugin SDK and Permissions Model

**Date:** 2025-07-17
**Status:** Accepted
**Deciders:** Core team

## Context

Plugins need a stable API to interact with the core runtime. M2 introduced a Plugin SDK with capability discovery, permission management, and event hooks. The permissions model grants plugins scoped access to system capabilities.

## Decision

The Plugin SDK provides:

- **PluginContext:** Runtime context passed to plugin handlers (plugin_id, capabilities, config, state)
- **CapabilityRequest:** Declares what the plugin needs (name + optional config)
- **CapabilityResponse:** Confirms granted capabilities with runtime config
- **CapabilityInfo:** Describes available capabilities (name, description, config schema)
- **PermissionManager:** Grants/revokes capabilities per plugin, tracks grants
- **Event hooks:** `on_start`, `on_stop`, `on_health_check` for lifecycle integration

Permissions model:
- Plugins declare capabilities they need at install time
- The runtime grants capabilities from what's available
- Missing capabilities don't fail install — they're reported as unmet
- Runtime can revoke capabilities at any time (plugin must handle gracefully)

## Consequences

- Plugin handlers receive a `PluginContext` as first argument
- Plugins should check `context.has_capability("x")` before using it
- The SDK is a separate package (`aios-plugin-sdk`) to keep core lean
- No wildcard permissions — each capability must be explicitly granted
- Event hooks are optional; plugins only implement what they need

## Alternatives Considered

1. **OS-style permissions (rwx):** Too coarse for capability-based system
2. **JWT tokens for capability grants:** Adds crypto overhead without benefit
3. **Implicit permissions (no declaration):** Dangerous; plugins could access everything

## References

- `packages/plugin-sdk/src/aios/plugin_sdk/context.py`
- `packages/plugin-sdk/src/aios/plugin_sdk/permissions.py`
- `tests/test_plugin_permissions.py`
