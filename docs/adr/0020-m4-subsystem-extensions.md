# ADR-0020: M4 Foundation Sub-System Extensions

**Date:** 2025-07-18
**Status:** Accepted
**Deciders:** Core team

## Context

M4.0–M4.9 delivered the AI Developer Platform foundation (capability catalog,
skills, approvals, connectors, MCP client/registry, secrets, workspaces,
artifacts, prompts, runtime wiring). Each milestone shipped only its minimum
viable checklist item. To reach production-grade completeness, M4.0–M4.8 were
deepened with the full checklist scope: hierarchy/merge tooling for the catalog,
additional first-party connectors, pluggable secret backends, workspace
sub-systems, artifact typing, role-based prompt templates, and a permission-gated
MCP platform service.

All extensions respect the frozen interfaces (`Permission`, `PermissionChecker`,
`PermissionSet`) and the ADR-0019 layering. No duplicate abstractions were
introduced — existing packages were extended in place.

## Decision

### Capability Catalog (M4.0)
`CapabilityCatalog` gains hierarchy tooling: `subtree(name)`, `depth(name)`,
`render_tree()`, and `merge(other)`. `merge` is idempotent (skips nodes already
present by name) so catalogs compose safely across layers.

### Connectors (M4.3)
`register_builtin_connectors` now wires five first-party connectors:
GitHub, Slack, Filesystem, **Gmail** (`gmail.send`/`gmail.read`/`gmail.draft`,
`NETWORK_HTTP`), and **Docker** (`docker.run`/`docker.build`/`docker.ps`,
`PROCESS_EXEC`). `FilesystemConnector` gains a `filesystem.list` binding.

### Secrets (M4.5)
`SecretBackend` implementations extended with `KeychainBackend` (optional
`keyring` dependency, in-memory fallback when unavailable) and
`RemoteVaultBackend` (HTTP `PUT`/`GET`/`DELETE` over `urllib` with bearer token).
Both are exported from `aios.secrets`.

### Workspaces (M4.6)
`Workspace` composes five sub-systems: `WorkspaceMemory`, `WorkspaceHistory`
(`HistoryEntry`), `WorkspaceCache`, `WorkspacePermissions`, and
`WorkspaceArtifacts`. `artifacts` is injected via `__init__` /
`WorkspaceManager.create` and surfaced as a property.

### Artifacts (M4.7)
`ArtifactKind` (`enum.StrEnum`: CODE/MARKDOWN/JSON/REPORT/PLAN) added.
`Artifact.kind` is persisted (incl. FilesystemBackend) and `ArtifactStore.put`
derives `content_type` from `kind` when not supplied.

### Prompts (M4.8)
`PromptRole` (`enum.StrEnum`: planner/coder/reviewer/research/system) and
`PromptVersion` (semver-tagged, immutable) added. Role builders
`planner_prompt` / `coder_prompt` / `reviewer_prompt` / `research_prompt` /
`system_prompt` are registered into the default library.

### MCP Service (M4.4 platform surface)
`services/mcp` was renamed `aios.mcp_service` to avoid the namespace collision
with the `packages/mcp` library, given its own `pyproject.toml`
(`aios-mcp-service`) and added to the workspace. `MCPPlatform` wraps
`aios.mcp.MCPRegistry`, exposes `add_server` (str or `MCPServerConfig`),
cached `discover`, `tools_for`, and a permission-gated `call` through
`PermissionSet`. Transport-only per ADR-0019.

## Consequences

- Each M4 milestone is now checklist-complete, not MVP-only.
- New code paths are covered by 107 tests across the touched modules; full
  changed-file lint is clean (pre-existing `services/gateway` and
  `services/orchestrator` lint debt is out of scope).
- `MCPPlatform` and the secret/workspace sub-systems provide the seams the
  M4.9 `DeveloperPlatform` composition root consumes.

## Compliance

- Frozen interfaces untouched.
- ADR-0019 layering preserved (MCP = transport; connectors ≠ integrations).
