# AIOS v0.6.6 — CLI (Priority 2)

**Release date:** 2025-07-18
**Type:** Minor (external-control surface completion — CLI)
**Supersedes:** v0.6.5 (gateway global goals WebSocket, ADR-0026)

## Summary

Completes **Priority 2** of the external-control roadmap: a production-quality
`aios` command-line interface over the gateway's existing REST + WebSocket
API. The AI OS is now operable from a terminal end-to-end, with no server-side
API changes.

Commands:

| Command | Purpose |
|---|---|
| `aios "<objective>" [--watch]` | Submit a goal; `--watch` follows it with a spinner |
| `aios goals [--watch]` | List tracked goals (`--watch` = live stream) |
| `aios goal <id>` | Full detail (tasks, result, events) |
| `aios status [id]` | Summary of all goals or one |
| `aios logs [id]` | Lifecycle `events` for a goal or all goals |
| `aios watch` | Live `WS /goals/ws` stream with screen redraw |
| `aios pause <id>` | Pause a running goal |
| `aios resume <id>` | Resume a paused / waiting-approval goal |
| `aios cancel <id>` | Cancel a goal |
| `aios retry <id>` | Retry a failed goal (fresh run of its objective) |
| `aios version` | Client + assistant version |
| `aios doctor` | Connectivity self-check (REST + WS) |
| `aios completion <bash\|zsh\|fish>` | Shell completion script |

Every command supports `--json` for machine-readable output. Colors are used
only when stdout is a TTY (graceful fallback). `run --watch` shows a progress
spinner; `Ctrl-C` leaves the goal running and exits `130`.

**Configurable identity:** the assistant name is read from `AIOS_ASSISTANT_NAME`
(default `AIOS`). The `aios` console script points at
`aios.supervisor.cli:main`; `aios-supervisor` and `aiosd` are unchanged.

## What Changed

- `services/supervisor/src/aios/supervisor/cli.py`: new CLI module (transport,
  commands, colors, spinner, completion, configurable name).
- `services/supervisor/pyproject.toml`: `aios` script → `cli:main`; added
  `httpx2`, `websockets` runtime deps.
- `ruff.toml`: per-file ignore for `cli.py` (`FBT*`, `E501` — long completion
  strings + boolean command args).
- `tests/test_aios_cli.py`: new — unit (parser, name config, json) + e2e
  against a real gateway (module-scoped uvicorn + offline Supervisor), watch
  mode, retry recreation.
- `docs/adr/0027-aios-cli.md`, `docs/RELEASE_v0.6.6.md`, `docs/CLI_REFERENCE.md`.

## Examples

```bash
export AIOS_GATEWAY_URL=http://localhost:8080

aios "Review my repo for security issues"
aios goals
aios watch
aios status
aios logs
aios pause <goal-id>
aios resume <goal-id>
aios cancel <goal-id>
aios retry <goal-id>
aios doctor
aios --json status
```

## Compliance

- FROZEN interfaces (`Skill*`, `aios.agents.permissions.*`) unchanged.
- **No server-side API changes** — the CLI consumes only existing REST/WS.
- Suite: **1173 passed, 55 skipped**. Ruff clean (`services/`, `tests/`;
  pre-existing `tests/test_browser.py` I001 excluded).

## Deferred

Offline direct-to-Supervisor fallback (would duplicate transport), and the
v0.7.0 stabilization phase (full integration against real Git/Browser/Notes/
Notifications workflows, edge-case hardening, install/packaging polish).

## Related

- ADR-0027 (this release), ADR-0026 (global goals WS), M5.1 gateway goals.
