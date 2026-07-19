# ADR-0023: AIOS Daemon & Proactive Briefings (M5.3 / M5.5)

**Date:** 2025-07-18
**Status:** Accepted
**Deciders:** Core team
**Supersedes:** ADR-0022 (native-first resolution)

## Context

M5.0–M5.2 delivered a native-first capability resolver, native desktop skills,
the Supervisor `/goals` API, and the `aios` REPL. To complete the AIOS product
experience two remaining capabilities were needed:

- **M5.3 — Daemon:** AIOS must run as a persistent background service, keep
  the Supervisor alive across the session, survive restarts via goal
  persistence, and host a scheduler for proactive work.
- **M5.5 — Proactive Briefings:** AIOS should proactively compose a morning
  briefing (notes, git, filesystem) and announce it via a desktop
  notification — without any user prompt and without any external service.

Both must obey the ADR-0022 rule: **fully offline, AIOS-native.** External
integrations are optional providers the resolver may prefer, never dependencies.

## Decision

### Daemon (`services/supervisor/daemon.py`)
- `Daemon` hosts a `Supervisor` and exposes `submit/pause/resume/cancel`
  passthroughs plus `status()` (uptime, goal count, briefing flag).
- Optional JSON-file persistence (`DaemonConfig.persist`, default `~/.aios/
  daemon/daemon-state.json`): goals + last briefing date survive restarts.
- Scheduler loop (`start`/`stop`) ticks every `tick_seconds` (default 60s) and
  triggers the briefing engine at most once per local day.
- `run_daemon()` + `aiosd` console script provide the long-running host.

### Proactive Briefing (`services/supervisor/briefing.py`)
- `BriefingEngine` composes a briefing objective from **native** capability
  sections only (`notes.review`, `git.recent`, `filesystem.reminders`), gated by
  what the resolver can actually resolve offline. Falls back to a minimal
  "check system status" when no native section is available.
- `compose_objective()` is deterministic: no-op before `after_hour` and once per
  calendar day (`last_run_date`).
- `announce()` delivers a desktop notification via `aios.desktop.notifications`
  (no-op when unavailable). `BriefingConfig.notify` disables it.

### Gateway surface (M5.3/5.5)
- `GET /daemon/status` → daemon uptime/goals/briefing flag.
- `POST /briefing/trigger` → compose (and schedule) today's briefing goal.
- Shared `Daemon` host via `get_daemon()`; the existing `Supervisor`/`/goals`
  API is unchanged.

## Consequences

- AIOS runs as a persistent, restart-safe service with zero external deps.
- Proactive morning briefings are fully native (notes/git/filesystem/notify).
- `aios-desktop` added as a workspace dependency of `aios-supervisor` (already a
  workspace member).
- Frozen interfaces (`Permission`, `PermissionChecker`, `PermissionSet`)
  untouched; native skills reuse existing catalog capabilities/permissions.
- New console scripts: `aios` (REPL), `aiosd` (daemon).

## Alternatives considered

- **Cron/systemd timer for briefings:** rejected — daemon-hosted scheduler keeps
  the briefing in-process with the same Supervisor and is portable (macOS/Linux/
  Windows) without OS-specific units.
- **LLM-generated briefing text:** deferred — M5.5 keeps briefing composition
  deterministic (native skill objective) so it works with no model configured.
