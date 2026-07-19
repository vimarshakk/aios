# Changelog

All notable changes to the AIOS project are documented here.

## v0.7.0 (2025-07-18) — Stabilization (RC)

Stabilization sprint: hardening, integration/failure-injection/security test
corpus, packaging fixes, and a live-gateway CLI smoke test of five workflows.
No new user-facing features.

### Fixed
- **Goal step desync (critical):** executor now syncs `goal.steps` from
  `step_results` so REST/WS/CLI show true per-step progress (was stuck at
  `pending`). `executor.py` + ADR-0028.
- **Note parsing (critical):** `save/capture/jot/store/keep a note titled X
  with body Y` now routes through `_split_note`; offline fallback parses
  title/body instead of hardcoding "Captured goal". `planner.py`.
- **Dockerfile:** `CMD` used a non-existent `python -m aios.gateway.main`;
  switched to the installed `aios-gateway` console script.
- **Version drift:** `aios-gateway` / `aios-supervisor` pinned at `0.1.0`;
  bumped to `0.7.0`.

### Added
- `tests/test_stabilization_e2e.py` — 22 integration / failure-injection /
  security / validation / orchestration tests (all passing).
- Docs: `QUICKSTART.md`, `EXAMPLES.md`, `TROUBLESHOOTING.md`,
  `RELEASE_v0.7.0.md`, `adr/0028`.

### Tests
- **1195 passed, 55 skipped** (network-gated). Exceeds the 1200-with-skips
  release threshold.

## v0.4.0 (2025-07-18)

### Added
- **M4 Deepening**: capability-catalog hierarchy/merge, Gmail + Docker connectors, `MCPPlatform` service, Keychain/RemoteVault secret backends, workspace sub-systems, `ArtifactKind`, role-based prompt templates
- **ADR-0020**: M4 foundation sub-system extensions

### Changed
- `services/mcp` renamed `aios.mcp_service` (own package `aios-mcp-service`) to avoid namespace collision with `packages/mcp`
- `ruff.toml` per-file-ignores extended for secrets, specialized agents/providers/tools, and `services/mcp`

### Fixed
- Vault round-trip test context-manager mock; `MCPPlatform`/`CapabilityCatalog.merge` test assertions

## v0.3.0 (2025-07-17)

### Added
- **M3.7 Vision Subsystem**: Image processing (format detection, resize, crop), OCR (Tesseract integration), and screenshot analysis
- **M3.8 Integrations Platform**: Third-party service integration framework with registry, config, lifecycle management
- **ADR-0011 through ADR-0018**: Architecture Decision Records for M2/M3 work

### Changed
- Fixed metrics snapshot bug (`rsplit` → `split`) in `aios.telemetry`
- Lazy playwright import in `aios.browser.BrowserSession`

## v0.2.0 (2025-07-16)

### Added
- **M2.1 Plugin SDK**: PluginContext, CapabilityRequest/Response, PermissionManager, event hooks
- **M2.2 Plugin Lifecycle**: start/stop/restart, dependency resolution, health checks
- **M2.3 Multi-Agent Execution**: TaskMessage, PriorityQueue, InMemoryQueue, Worker, WorkerPool
- **M2.4 Fault Tolerance**: RetryPolicy, DeadLetterQueue, TaskPersistence
- **M2.5 Runtime Orchestrator**: RuntimeOrchestrator ties everything together

## v0.1.0 (2025-07-15)

### Added
- **M1 Foundation**: Core runtime, event bus, plugin system, context engine, memory
- **8 phases** completed: architecture, core runtime, event system, plugin manifest, context engine, memory, plugin loader, integration tests
- 453 tests at Foundation Freeze
- Frozen interfaces documented in `docs/FROZEN_INTERFACES.md`
