# M4 — AI Developer Platform (Foundation)

**Status:** M4.0–M4.9 complete; M4.0–M4.8 deepened to full checklist scope (107 tests on touched modules, changed-file lint clean). See `docs/adr/0020-m4-subsystem-extensions.md`.
**Scope:** Platform-focused foundation respecting frozen interfaces (docs/FROZEN_INTERFACES.md) and ADR-0019 layered architecture.

## Milestones

| ID | Milestone | Package / Service | Status | Tests | Deepening |
|----|-----------|-------------------|--------|-------|-----------|
| M4.0 | Capability Catalog | `packages/agents` (`capability_catalog.py`) | ✅ Done | 21 | ✅ subtree/depth/render_tree/merge |
| M4.1 | Skills System | `packages/skills` | ✅ Done | 24 | — |
| M4.2 | Approval & Policy | `packages/security/policy/` | ✅ Done | 13 | — |
| M4.3 | Connectors | `packages/integrations/` | ✅ Done | 11 | ✅ Gmail + Docker connectors; filesystem.list |
| M4.4 | MCP | `packages/mcp` (client/registry/mapping) + `services/mcp` (MCPPlatform) | ✅ Done | 13 | ✅ `aios.mcp_service`, permission-gated `MCPPlatform` |
| M4.5 | Secrets | `packages/secrets/` | ✅ Done | 9 | ✅ KeychainBackend + RemoteVaultBackend |
| M4.6 | Workspaces | `packages/workspaces/` | ✅ Done | 9 | ✅ memory/history/cache/permissions/artifacts sub-systems |
| M4.7 | Artifacts | `packages/artifacts/` | ✅ Done | 6 | ✅ ArtifactKind + persisted `kind` |
| M4.8 | Prompts | `packages/prompts/` | ✅ Done | 9 | ✅ PromptRole/PromptVersion + role builders |
| M4.9 | Runtime Wiring | `packages/platform/` + gateway | ✅ Done | 7 | — |

## Design Rules (user-mandated)
1. Do NOT modify frozen interfaces (`Permission`, `PermissionChecker`, `PermissionSet`).
2. Do NOT create duplicate abstractions (use existing `CapabilityRegistry`, `Integration` base, security primitives).
3. Extend existing packages; build new platform packages only where the concern is genuinely new.
4. Everything composable & reusable; layered per ADR-0019:
   `Agent → Skill → Capability → Permission (frozen) → Connector → Integration`.

## Commands
- Lint: `uv run --with ruff ruff check packages/ tests/`
- Tests: `uv run pytest <path> -p no:cacheprovider -q`
- Sync: `uv sync --all-packages -p 3.12`

## Notes
- `packages/skills` depends on `aios-core` + `aios-agents` (added to workspace + sources in root pyproject.toml).
- pytest.ini updated with `asyncio_mode = auto` (was overriding pyproject, breaking async tests).
- Lint config lives in `ruff.toml` (root), NOT pyproject `[tool.ruff]`. `packages/**/src/**` ignores SLF001/BLE001/TRY300.
- `services/mcp` renamed `aios.mcp_service` (own `pyproject.toml`, added to workspace) to avoid namespace collision with `packages/mcp`.
- `ruff.toml` per-file-ignores extended: `packages/secrets/**` → `S310`; `packages/agents/.../specialized`, `packages/providers`, `packages/tools` → `ARG002`; `services/mcp` → `FBT001/002/003/BLE001/T201`.
- `services/gateway` + `services/orchestrator` pre-existing lint debt resolved: broad `except Exception` → specific (`httpx.HTTPError`/`OSError`/`TimeoutError`), `logging` added, `SLF001` via `getattr`, `SIM108` fallback, `TC003/TC001` imports moved to `TYPE_CHECKING`.
- Full suite now runnable: `tests/conftest.py` deselects `network`-marked tests (httpbin.org live calls) by default; run with `-m network` to opt in. `1115 passed, 55 skipped`.

## Post-M4 Strategy (frozen primitives → M5 AIOS)

M4 shipped the platform *primitives*. The next layer is **autonomous goal
execution**, not more primitives:

- **Freeze platform primitives after M4.** No new connectors/skills/agents
  beyond what M5 needs. Extend in place only.
- **Supervisor service (`services/supervisor`)**: top-level owner of long-running
  goals — plan → task graph → skill scheduler → connectors → verify → memory →
  report, with pause/resume/approval/retry. Composes `DeveloperPlatform`; does
  not reimplement planning/execution (ADR-0021).
- **Consume Composio instead of building SaaS connectors**: `ComposioConnector`
  + `ComposioIntegration` adapt Composio's managed OAuth + tool catalog into the
  ADR-0019 `Connector`/`Integration` contract. `composio` is an optional,
  lazy-imported dependency. Curated bindings for GitHub/Notion/Gmail/Slack/Linear
  plus dynamic `action=<SLUG>` execution.
- **M5 AIOS Desktop** drives the Supervisor over the gateway transport.

### New in this pass
- `services/supervisor` package (`aios-supervisor`): `Supervisor`, `Goal`,
  `GoalStatus`, `StepRecord`, `ApprovalRequest`; `main.run()` entrypoint.
- `packages/integrations/src/aios/integrations/composio/__init__.py`:
  `ComposioConnector`, `ComposioIntegration`; wired into
  `register_builtin_connectors` (key `composio`).
- `DeveloperPlatform.capabilities_for_skill(name)` — read-only seam for the
  Supervisor's approval gating.
- `docs/adr/0021-supervisor-and-composio.md`.
- Tests: `tests/test_composio_connector.py`, `tests/test_supervisor.py`.
- Full suite: `1129 passed, 55 skipped` (network tests deselected). Lint clean.

### M5 — AIOS Core (native-first, offline-capable) — ✅ v0.6.0

Delivers the core M5 product promise: AIOS runs **completely offline** with
AIOS-native capabilities; external integrations are optional providers the
resolver prefers when connected, never required (ADR-0022).

- `packages/platform/src/aios/platform/resolver.py`: new `CapabilityResolver`,
  `ProviderKind` (NATIVE/CONNECTOR/MCP), `Resolution`; native-first
  `resolve(capability)`. `DeveloperPlatform` gains `resolve()` +
  `register_provider()`; `bootstrap()` registers native skills as preferred.
- `packages/skills/src/aios/skills/native/__init__.py`: `TerminalSkill`,
  `FilesystemSkill`, `GitSkill`, `DockerSkill`, `NotesSkill`, `NotifySkill`;
  `register_native_skills(registry, resolver)`. All offline, bound to catalog
  capabilities + frozen permissions.
- `services/gateway/src/aios/gateway/main.py`: Supervisor `/goals` REST +
  `WS /goals/{id}/events` (M5.1) over shared `get_supervisor()`.
- `services/supervisor/src/aios/supervisor/main.py`: `aios` interactive REPL
  (M5.2); `aios` console script in `pyproject.toml`.
- `docs/adr/0022-native-first-capability-resolution.md`,
  `docs/RELEASE_v0.6.0.md`.
- Tests: `tests/test_capability_resolver.py` (5), `tests/test_native_skills.py`
  (5), `tests/test_supervisor_api.py` (2).
- Full suite: `1141 passed, 55 skipped` (no regressions). New code lint clean.
- Remaining: `tests/test_browser.py` has a pre-existing I001 import-sort lint
  error (unrelated file, unchanged in this pass) — out of scope for M5.

### M5.3 / M5.5 — AIOS Daemon & Proactive Briefings — ✅ v0.6.1

M5 complete: AIOS runs as a persistent, restart-safe background service and
proactively delivers a native-only morning briefing (ADR-0023).

- `services/supervisor/src/aios/supervisor/daemon.py`: `Daemon` + `DaemonConfig`
  — hosts `Supervisor`, goal persistence (JSON), scheduler loop, `run_daemon()`;
  `aiosd` console script.
- `services/supervisor/src/aios/supervisor/briefing.py`: `BriefingEngine` +
  `BriefingConfig` — native-only briefing composition (notes/git/filesystem),
  once-daily after `after_hour`, desktop notification via `aios.desktop`.
- Gateway: `GET /daemon/status`, `POST /briefing/trigger`, shared `get_daemon()`.
- `aios-desktop` added as workspace dependency of `aios-supervisor`
  (+ `tool.uv.sources` entry in root pyproject).
- `docs/adr/0023-aios-daemon-briefings.md`, `docs/RELEASE_v0.6.1.md`.
- Tests: `tests/test_daemon_briefing.py` (8).
- Full suite: `1149 passed, 55 skipped` (no regressions). New code lint clean.

### M5 — Native Browser Skill (final capability) — ✅ v0.6.2

Completes the native execution stack: `BrowserSkill` is the last missing
native desktop capability, built on the in-repo `aios.browser.BrowserSession`.

- `packages/skills/src/aios/skills/native/browser_skill.py`: `BrowserSkill` +
  `BrowserConfigOpts`, `BROWSER_CAPABILITIES`. Navigation (open/search/back/
  forward/refresh), tab management, automation (click/type/press/scroll/
  wait_for/evaluate/screenshot/extract_text), downloads, plus a security model:
  domain allowlist, localhost/internal SSRF guard, confirmation for destructive
  actions (close_tab/download), configurable timeout, and an audit log.
- Wired into `register_native_skills` (capabilities `browser.*` resolve NATIVE
  via `CapabilityResolver`); exported from `aios.skills.native`.
- `aios-browser` added as a workspace dependency of `aios-skills`.
- `docs/adr/0022-*.md` native skills table updated; `docs/RELEASE_v0.6.2.md`.
- Tests: `tests/test_browser_skill.py` (11) using an injected fake session.
- Full suite: `1160 passed, 55 skipped` (no regressions). New code lint clean.
- M5 native capabilities now complete: terminal, filesystem, git, docker,
  notes, notify, browser.

### M6 — Autonomous Planner & Native Goal Runner (AIOS autonomy) — ✅ v0.6.3

Turns a natural-language objective into a validated, typed task graph (DAG) and
executes it through native skills via the `CapabilityResolver`, with human
approval gates for sensitive operations. Deterministic-first: known intents are
handled by offline templates; an (optional, recommended) LLM fallback handles
novel goals.

- `services/supervisor/src/aios/supervisor/task_graph.py`: `Task`, `TaskGraph`,
  `validate_task_graph` (unique ids, known deps, cycle detection,
  `to_dict`/`from_dict`).
- `services/supervisor/src/aios/supervisor/planner.py`: `AutonomousPlanner`
  deterministic-first hybrid — 6 intent templates (`hackernews`, `open`,
  `commit`, `docker`, `create_note`, `summarize`), the `summarize` pipeline
  (`browser` → `llm.summarize` → `notes` → `notify`), optional LLM fallback with
  strict JSON schema + fence parsing, and a safe offline fallback.
- `services/supervisor/src/aios/supervisor/executor.py`: `NativeGoalRunner`
  bridges the planner's DAG to `aios.workflows.WorkflowExecutor`; each
  `tool_call` step resolves (`platform.resolve`) and executes
  (`platform.execute_skill`). Pre-flight approval gate for `external:` /
  `destructive:` / `publish:` → `GoalStatus.WAITING_APPROVAL`.
- `Supervisor` wiring: `submit()` plans + runs via planner + runner (accepts
  `llm_fn`, `planner_timeout_seconds`); `resume()` reuses the persisted
  `task_graph`. `Goal.to_dict()` enriched with `task_graph` / `events` /
  `workflow_result`.
- `docs/adr/0024-autonomous-planner.md`, `docs/RELEASE_v0.6.3.md`.
- Tests: `services/supervisor/tests/test_m6_planner.py` (10) + migrated
  `tests/test_supervisor.py` (5) / `tests/test_daemon_briefing.py` (8).
- Full suite: `1159 passed, 55 skipped` (no regressions). New code lint clean.
- Deferred to M6.1: parallel execution, retries, plan reflection self-correction
  (hooks already present in `WorkflowExecutor`).

### M6.1 — Parallel Execution, Retry Policies & Reflection — ✅ v0.6.4

Hardens the autonomous pipeline (ADR-0025) without changing the architecture
or frozen contracts. A single topological scheduler in `NativeGoalRunner` adds
three autonomy capabilities:

- **Parallel execution** — independent ready-set tasks run concurrently via
  `asyncio.gather`; dependents wait. `parallel` flag (default `True`).
- **Retry policies** — `Task.retry = {"max_retries", "backoff_seconds"}`;
  `AutonomousPlanner._apply_defaults` injects a bounded retry onto `browser.` /
  `git.` / `docker.` steps. Failed attempts emit `retry` events and self-heal.
- **Reflection / dynamic replanning** — `Task.reflect` + optional
  `reflection_fn(task, output, graph)` hook fires after each reflected step and
  may mutate the live graph (swap a capability, append a discovered step). The
  scheduler re-reads `graph.tasks` each iteration, so injected tasks run. The
  planned graph is re-snapshotted at end of execution so reflection-injected
  steps persist on the goal and stream over `/goals`.

- `task_graph.py`: `Task.retry` / `Task.reflect` (+ serialization).
- `planner.py`: `_apply_defaults` retry injection on network/IO-prone caps.
- `executor.py`: parallel scheduler with retry + reflection; `parallel` /
  `reflection_fn` options; richer `workflow_result` + per-step `events`.
- `supervisor.py`: exposes `parallel` / `reflection_fn` (legacy
  `max_step_attempts` retained for compatibility).
- `docs/adr/0025-parallel-retry-reflection.md`, `docs/RELEASE_v0.6.4.md`.
- Tests: +4 M6.1 tests (`test_m6_planner.py`); `test_daemon_resume_runs_goal`
  migrated to a single event loop.
- Full suite: `1159 passed, 55 skipped` (no regressions). New code lint clean.

### Priority 1 — External Control Surface (REST + global event stream) — ✅ v0.6.5

Completes the user-mandated **Priority 1** roadmap item: expose Supervisor
control over the gateway. The M5.1 gateway already shipped the full REST
control surface and a per-goal `WS /goals/{id}/events`:

- `POST /goals` (submit objective) · `GET /goals` (list) ·
  `GET /goals/{id}` (full `Goal.to_dict()`)
- `POST /goals/{id}/pause` · `/resume` · `/cancel`
- `WS /goals/{id}/events` (per-goal progress)

This release adds the missing **global, multi-goal** view:

- `WS /goals/ws` (`goals_stream`) — single connection streaming *all* goals as
  they change: initial `snapshot`, change-triggered `snapshot` frames (250ms
  poll, cheap `status`+`len(events)` fingerprint), and a terminal `done` frame
  (closes once every goal is terminal). Wire-compatible with `Goal.to_dict()`,
  so it shares shape with `GET /goals` and the per-goal WS (ADR-0026).

- `services/gateway/src/aios/gateway/main.py`: `WS /goals/ws`.
- `services/gateway/pyproject.toml`: `[dependency-groups].dev = ["httpx2>=0.28"]`
  (newer starlette's `TestClient` requires `httpx2`).
- `tests/test_gateway_goals_ws.py`: new — route + offline fake-platform test
  (snapshot contains seeded goal + terminal `done` frame).
- `docs/adr/0026-gateway-global-goals-stream.md`, `docs/RELEASE_v0.6.5.md`.
- Full suite: `1161 passed, 55 skipped` (no regressions). New code lint clean.

### Priority 2 — AIOS CLI (terminal control surface) — ✅ v0.6.6

Completes the user-mandated **Priority 2** roadmap item: a production-quality
`aios` CLI over the existing gateway REST + `WS /goals/ws` surface (no new
server APIs). Commands: `run [--watch]`, `goals [--watch]`, `goal <id>`,
`status [id]`, `logs [id]`, `watch`, `pause/resume/cancel/retry <id>`,
`version`, `doctor`, `completion <bash|zsh|fish>`. Every command honors
`--json`; colors only on TTY; `run --watch` spinner; `Ctrl-C` leaves the goal
running (exit 130).

- **Configurable identity** — assistant name from `AIOS_ASSISTANT_NAME`
  (default `AIOS`); core code never hard-codes it (ADR-0027).
- `services/supervisor/src/aios/supervisor/cli.py`: transport (`httpx2` REST +
  `websockets` WS), commands, ANSI colors, spinner, completion, name config.
- `services/supervisor/pyproject.toml`: `aios` → `cli:main`; added `httpx2`,
  `websockets`; `ruff.toml` per-file ignore for `cli.py` (`FBT*`, `E501`).
- `tests/test_aios_cli.py`: unit (parser, name config, json) + e2e against a
  real gateway (module-scoped uvicorn + offline `Supervisor`), watch + retry.
- `docs/adr/0027-aios-cli.md`, `docs/RELEASE_v0.6.6.md`, `docs/CLI_REFERENCE.md`.
- Full suite: `1173 passed, 55 skipped` (no regressions). New code lint clean.

### M6.2+ — suggested next (not in this release)

- Long-term memory (preferred editor/repo/profile) feeding the planner.
- Multi-agent coordination (research / coding / test / docs agents + coordinator).
- API/CLI polish: richer `/goals` status, plan-preview `aios` command,
  end-to-end integration tests, release packaging.
