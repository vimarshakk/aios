# ADR-0007: Permission Model — Declarative Access Control

**Status:** Accepted  
**Date:** 2026-07-17  
**Deciders:** AIOS Core Team

## Problem

Tools and plugins need different levels of access (filesystem, network, desktop, database). No mechanism exists to declare, check, or enforce permissions before tool execution.

## Decision

Implement a declarative permission model with:
- `Permission` constants (11 well-known permissions as string constants)
- `PermissionSet` (frozenset-backed, immutable after construction)
- `PermissionChecker` (check, enforce, grant, revoke, interactive approval via `on_request` callback)

```python
class Permission:
    FILESYSTEM_READ = "filesystem.read"
    NETWORK_HTTP = "network.http"
    PROCESS_EXEC = "process.exec"
    # ... 11 total

class PermissionSet:
    def has(perm: str) -> bool: ...
    def has_all(perms: Sequence[str]) -> bool: ...
    def missing(perms: Sequence[str]) -> list[str]: ...

class PermissionChecker:
    def check(required: Sequence[str]) -> bool: ...
    def enforce(required: Sequence[str]) -> PermissionResult: ...
    def enforce_tool(tool: BaseTool) -> PermissionResult: ...
```

## Rationale

- **Declarative:** Tools declare required permissions via `BaseTool.permissions` class attribute. No runtime introspection needed.
- **Immutable sets:** `PermissionSet` uses `frozenset` — no mutation after construction. Safe for concurrent use.
- **Interactive approval:** `on_request` callback enables GUI/CLI approval prompts without hard-coding UI logic.
- **Tool-aware:** `enforce_tool()` reads permissions from `BaseTool.permissions` automatically.

## Alternatives Considered

1. **Role-based access control (RBAC):** Over-engineered for M1 — single-user system. Could be layered on in M2 for multi-user deployments.
2. **OS-level permissions (Unix perms):** Rejected — too coarse for AI tool execution (e.g., "network.http" vs "network.tcp").
3. **Capability-based security:** Considered but deferred — `PermissionSet` is a simplified capability model.

## Consequences

- `PermissionRequest` / `PermissionResult` are frozen dataclasses — immutable audit trail.
- `PermissionChecker.enforce()` returns `PermissionResult` with `approved` property — no exceptions for flow control.
- Tools without declared permissions are treated as unrestricted.
- `on_request` callback enables interactive flows without coupling to any UI framework.

## Future Evolution

- M2: Multi-user RBAC (admin, developer, viewer roles).
- M2: Permission policies (time-based, context-based, location-based).
- M3: Audit logging for all permission decisions.
