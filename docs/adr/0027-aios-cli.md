# ADR-0027: AIOS CLI (Priority 2 — External Control Surface)

**Status:** Accepted
**Date:** 2025-07-18
**Supersedes:** — (extends ADR-0026 global goals stream, M5.1 gateway goals)

## Context

Priority 1 delivered the gateway's external-control REST + WebSocket surface
(`POST /goals`, `GET /goals`, `GET /goals/{id}`, pause/resume/cancel, and
`WS /goals/ws`). The platform is now fully controllable over HTTP, but there is
no first-class terminal user interface — operators must `curl` the API by hand.
Priority 2 makes the system *usable from the command line* (user roadmap),
without any server-side API changes.

Two design constraints were mandated by the user:

1. **No new server APIs** — the CLI must consume only the existing REST/WS
   contracts (`Goal.to_dict`, `WS /goals/ws`).
2. **Configurable assistant identity** — the name must be a configuration value
   (`AIOS_ASSISTANT_NAME`), not hard-coded, so the product identity can be
   adjusted without touching core code.

## Decision

Build `aios.supervisor.cli` — an `aios` console script that is a thin,
production-quality client over the gateway:

- **Transport:** `httpx2.AsyncClient` for REST, `websockets` for `WS /goals/ws`.
  Target is `AIOS_GATEWAY_URL` (default `http://localhost:8080`).
- **Assistant name:** `assistant_name()` reads `AIOS_ASSISTANT_NAME`
  (default `AIOS`); the argparse `prog` and `doctor`/`run` banners derive
  from it. Rebranding is a one-line env change.
- **Commands** (all honor `--json`):
  - `run "<objective>" [--watch]` — submit + optional spinner follow.
  - `goals [--watch]` — list; `--watch` aliases `watch`.
  - `goal <id>` — full detail (tasks, result).
  - `status [id]` — all goals or one.
  - `logs [id]` — lifecycle `events` for a goal or all goals.
  - `watch` — live `WS /goals/ws` stream with screen redraw.
  - `pause <id>` / `resume <id>` / `cancel <id>` — map to gateway actions.
  - `retry <id>` — for a *failed* goal, submit a fresh goal with the same
    objective (API-compatible; `resume` only handles paused/approval).
  - `version` / `doctor` — client/assistant version; connectivity self-check.
  - `completion <bash|zsh|fish>` — emits a shell completion script.
- **UX:** human-friendly tables by default; `--json` for every command;
  ANSI colors only when stdout is a TTY (graceful fallback); `run --watch`
  shows a spinner; `Ctrl-C` leaves the goal running and exits 130.

The `aios` console script points at `aios.supervisor.cli:main`
(`aios-supervisor` and `aiosd` remain on `main`).

## Consequences

- **Positive:** The AI OS is now operable from a terminal end-to-end
  (`aios "Review my repo"`, `aios watch`, `aios logs`, etc.).
- **Positive:** Configurable via env var; core planner/supervisor/memory untouched.
- **Positive:** `--json` + stable `Goal.to_dict` shape makes the CLI scriptable
  and a natural foundation for a future TUI / desktop wrapper.
- **Negative:** Adds `httpx2` + `websockets` to the supervisor runtime deps
  (already transitive; now explicit).
- **Negative:** The CLI depends on a running gateway; there is no offline
  direct-to-Supervisor fallback yet (deferred — would duplicate transport).

## Compliance

- FROZEN interfaces (`Skill*`, `aios.agents.permissions.*`) untouched.
- **No server-side API changes** — only consumes existing REST/WS.
- Suite: **1173 passed, 55 skipped**. Ruff clean (`services/`, `tests/`;
  pre-existing `tests/test_browser.py` I001 excluded).

## Tests

`tests/test_aios_cli.py` — parser/command coverage, configurable name,
`--json` shape, and end-to-end commands against a real gateway app backed by
an offline `Supervisor` (module-scoped uvicorn fixture). Watch mode and retry
recreation are exercised.

## Related

- ADR-0026 (global goals WS), ADR-0022 (native-first), M5.1 gateway goals.
