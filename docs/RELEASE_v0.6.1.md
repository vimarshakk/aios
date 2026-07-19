# AIOS v0.6.1 — Daemon & Proactive Briefings

**Release date:** 2025-07-18
**Type:** Minor (M5.3 daemon, M5.5 briefings)
**Supersedes:** v0.6.0 (native-first core, ADR-0022)

## Summary

M5 is complete. AIOS now runs as a persistent, restart-safe background
service (`aiosd`) that keeps the Supervisor alive, persists goals to disk, and
proactively delivers a morning briefing composed entirely from AIOS-native
capabilities (notes, git, filesystem, desktop notifications). External
integrations remain optional providers — AIOS works fully offline.

## What's New

### AIOS Daemon (M5.3) — `services/supervisor/daemon.py`
- `Daemon` hosts a `Supervisor`; `submit/pause/resume/cancel` passthroughs,
  `status()` (uptime, goal count, briefing flag).
- Optional JSON persistence (`~/.aios/daemon/daemon-state.json`) — goals and
  last-briefing date survive restarts.
- Scheduler loop triggers the briefing at most once per local day.
- `run_daemon()` + `aiosd` console script.

### Proactive Briefings (M5.5) — `services/supervisor/briefing.py`
- `BriefingEngine` composes a native-only briefing objective (notes/git/
  filesystem), gated by resolver capability availability; one per day, after
  `after_hour`. Falls back to a minimal status check.
- `announce()` via `aios.desktop.notifications` (no-op when unavailable).

### Gateway
- `GET /daemon/status`, `POST /briefing/trigger`; shared `get_daemon()` host.

## Quality

- Lint: `ruff check packages/ services/` — clean (new code).
- Tests: **1149 passed, 55 skipped** (full suite, no regressions).
- New tests: `tests/test_daemon_briefing.py` (8).
- Frozen interfaces (`Permission`, `PermissionChecker`, `PermissionSet`)
  untouched.
- `aios-desktop` added as a workspace dependency of `aios-supervisor`.

## Upgrade Notes

- No schema/migration changes.
- New console scripts: `aios` (REPL), `aiosd` (daemon). Run `aiosd` to
  start the persistent service; it auto-runs the morning briefing when due.
- Native briefing sections require the corresponding local binaries only when
  the goal executes (git); missing binaries degrade that section gracefully.
