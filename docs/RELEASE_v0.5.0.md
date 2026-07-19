# Release v0.5.0 — Supervisor Service & Composio Consumption

**Date:** 2025-07-18

## Highlights

Building on the M4 platform primitives, this release adds the **top-level
autonomous goal-execution layer** (the lead-in to M5 AIOS Desktop) and
**consumes Composio** for the SaaS integration surface instead of building
first-party connectors. No platform primitives were modified; the Supervisor
composes `DeveloperPlatform` and the Composio connector adapts the existing
`Connector`/`Integration` contract. See `docs/adr/0021-supervisor-and-composio.md`.

## Added

- **`services/supervisor`** (`aios-supervisor`): top-level goal orchestration.
  - `Supervisor` — composes `DeveloperPlatform`; plans a goal, schedules steps
    as a resumable task graph, gates each step through policy/approval, retries
    failed steps, and records outcomes to goal state + workspace.
  - `Goal` / `GoalStatus` / `StepRecord` — goal lifecycle and progress model.
  - `ApprovalRequest` + `approval_callback` — human-in-the-loop gate for
    `external:` / `destructive:` / `publish:`-prefixed capabilities; halts in
    `WAITING_APPROVAL` and resumes on `resume()`.
  - `pause()` / `resume()` / `cancel()` control methods.
  - `main.run()` self-runnable entrypoint (`aios-supervisor` console script).
- **`ComposioConnector` + `ComposioIntegration`** (`packages/integrations`):
  - Thin transport mapping Composio tool slugs onto `composio.tools.execute`
    (conforms to frozen `Integration` ABC).
  - Curated catalog-visible bindings for GitHub/Notion/Gmail/Slack/Linear.
  - Dynamic discovery-driven execution via `invoke(cap, perms, action=<SLUG>)`
    and `discover(toolkits=...)`.
  - `composio` is an **optional, lazy-imported** dependency; clear `ImportError`
    when used without the SDK. Wired into `register_builtin_connectors`
    (key `composio`).
- **`DeveloperPlatform.capabilities_for_skill(name)`** — read-only seam used by
  the Supervisor for approval gating.
- **`docs/adr/0021-supervisor-and-composio.md`**.

## Tests

- `tests/test_composio_connector.py` — curated bindings, dynamic invoke,
  permission denial, discovery (mocked SDK).
- `tests/test_supervisor.py` — run-to-completion, retry/failure, approval gate
  (callback + no-callback), pause/cancel, progress.

## Status

- Lint: `uv run --with ruff ruff check packages/ services/ tests/` — clean.
- Tests: `1129 passed, 55 skipped` (network tests deselected via
  `tests/conftest.py`).
- No modifications to frozen interfaces (`Permission`, `PermissionChecker`,
  `PermissionSet`).
