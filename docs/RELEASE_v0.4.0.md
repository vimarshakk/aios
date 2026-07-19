# Release v0.4.0 — AI Developer Platform (M4 Deepening)

**Date:** 2025-07-18

## Highlights

M4.0–M4.9 delivered the AI Developer Platform foundation. This release deepens
M4.0–M4.8 to full checklist scope and adds the permission-gated MCP platform
service. See `docs/adr/0020-m4-subsystem-extensions.md`.

## Added

- **M4.0 Capability Catalog**: `subtree()`, `depth()`, `render_tree()`, and
  idempotent `merge()` for composing catalogs across layers.
- **M4.3 Connectors**: first-party `GmailConnector` (send/read/draft,
  `NETWORK_HTTP`) and `DockerConnector` (run/build/ps, `PROCESS_EXEC`);
  `filesystem.list` binding. `register_builtin_connectors` now covers
  GitHub, Slack, Filesystem, Gmail, Docker.
- **M4.4 MCP Platform**: `aios.mcp_service.MCPPlatform` — wraps
  `aios.mcp.MCPRegistry`, `add_server` (str | `MCPServerConfig`), cached
  `discover`, `tools_for`, and permission-gated `call` via `PermissionSet`.
  `services/mcp` split into its own `aios-mcp-service` package to avoid the
  namespace collision with `packages/mcp`.
- **M4.5 Secrets**: `KeychainBackend` (optional `keyring`, in-memory fallback)
  and `RemoteVaultBackend` (HTTP PUT/GET/DELETE over `urllib`, bearer token).
- **M4.6 Workspaces**: `WorkspaceMemory`, `WorkspaceHistory` (+`HistoryEntry`),
  `WorkspaceCache`, `WorkspacePermissions`, `WorkspaceArtifacts` composed into
  `Workspace`; `artifacts` injected via constructor / manager.
- **M4.7 Artifacts**: `ArtifactKind` `StrEnum` (CODE/MARKDOWN/JSON/REPORT/PLAN);
  `Artifact.kind` persisted (incl. FilesystemBackend); `put` derives
  `content_type` from `kind`.
- **M4.8 Prompts**: `PromptRole` `StrEnum` (planner/coder/reviewer/research/
  system), immutable `PromptVersion` (semver), and role builders
  (`planner_prompt` / `coder_prompt` / `reviewer_prompt` / `research_prompt` /
  `system_prompt`) registered into the default library.

## Changed

- `aios.secrets` now exports `KeychainBackend`, `RemoteVaultBackend`.
- `aios.artifacts` now exports `ArtifactKind`; `aios.workspaces` exports the
  sub-system classes; `aios.prompts` exports `PromptRole`/`PromptVersion` and
  role builders.
- `ruff.toml` per-file-ignores extended (secrets `S310`; specialized agents /
  providers / tools `ARG002`; `services/mcp` `FBT*`/`BLE001`/`T201`).
- Root `pyproject.toml` workspace members include `services/mcp`.

## Fixed

- `tests/test_secrets.py` vault round-trip mock now exercises a real context
  manager so `RemoteVaultBackend` encrypt/decrypt paths are covered.
- `MCPPlatform.test_add_server_registers` asserts `len(registry.servers)`.
- `CapabilityCatalog.merge` dedupe test registers a single new node.

## Compliance

- Frozen interfaces (`Permission`, `PermissionChecker`, `PermissionSet`)
  untouched.
- ADR-0019 layering preserved (MCP = transport only; connectors ≠ integrations).

## Test / Lint

- Full repo `ruff check` is clean (was 31 pre-existing errors in `services/gateway`
  + `services/orchestrator`; now resolved: specific exception handling, `logging`,
  `getattr` for private access, `TYPE_CHECKING` imports).
- Full suite runnable: `tests/conftest.py` deselects `network`-marked tests
  (live httpbin.org calls) by default. `1115 passed, 55 skipped` in ~17s.
- Run network tests explicitly with `-m network`.
