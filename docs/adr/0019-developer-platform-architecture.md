# ADR-0019: AI Developer Platform — Canonical Layered Architecture

**Date:** 2025-07-17
**Status:** Accepted
**Deciders:** Core team

## Context

M4 introduces developer-platform capabilities (skills, connectors, approvals,
MCP, secrets, workspaces, artifacts, prompts). Without explicit architecture
rules, these would spawn parallel abstractions that duplicate existing systems
(integrations, MCP service, frozen permissions) and make autonomous planning
harder as the package count grows into the hundreds.

## Decision

AIOS has **one layered platform**, not a collection of separate subsystems:

```
Agent
  → Skill          (orchestrates capabilities; declares required capabilities)
    → Capability   (hierarchical catalog entry, e.g. filesystem.write)
      → Permission (frozen: aios.agents.permissions.Permission)
        → Connector (implementation of one integration's capability)
          → Integration (external system: GitHub, Slack, Docker, ...)
            → MCP (OPTIONAL transport for remote connectors only)
```

### Rules (mandatory)

1. **One abstraction per concern.** No parallel implementations.
2. **No duplicate frameworks.** Connectors ≠ Integrations ≠ MCP. They are layers.
3. **Extend before creating.** `integrations`, `security`, `mcp` are extended,
   not replaced.
4. **MCP is transport, not integration logic.** It discovers/exposes/proxies
   connectors. It never becomes another plugin or integration framework.
5. **Integrations own external systems.** Connectors live inside
   `packages/integrations/<service>/`.
6. **Skills orchestrate capabilities; they do not implement tools.**
7. **Permissions are immutable contracts.** Policy/approval layers extend
   behavior but never replace the `Permission` / `PermissionChecker` /
   `PermissionSet` API.

### What is explicitly forbidden in M4

- ✗ Separate `packages/connectors` framework
- ✗ New permission framework
- ✗ Second capability registry
- ✗ Second marketplace
- ✗ Duplicate MCP implementation

## Consequences

- `packages/skills` is the only genuinely new package in M4.
- `packages/secrets`, `packages/workspaces`, `packages/artifacts`,
  `packages/prompts` are new but independent (no overlap with existing code).
- `packages/integrations` gains concrete connector implementations.
- `packages/security` gains a `policy/` subpackage (approval + rules).
- `services/mcp` gains client/registry/discovery/permissions modules.
- `packages/agents/registry.py` (CapabilityRegistry) is extended with a
  **capability catalog** (hierarchical taxonomy) — but the existing registry
  API stays unchanged.
- Frozen interfaces (`docs/FROZEN_INTERFACES.md`) remain untouched.

## References

- `docs/FROZEN_INTERFACES.md` (locked v1.0)
- `packages/integrations/` (M3.8 base)
- `packages/security/` (M1)
- `services/mcp/` (M3 partial)
- `packages/agents/permissions.py` (frozen)
