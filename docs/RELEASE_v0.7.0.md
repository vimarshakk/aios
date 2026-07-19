# Release v0.7.0 — Stabilization & Quality Hardening

**Release date:** 2025-07-18
**Type:** Patch (quality hardening, zero new features)
**Supersedes:** v0.6.6 (CLI + external control surface, ADR-0027)

## Summary

v0.7.0 is a stabilization pass over the v0.6.x autonomous pipeline. No new
features were added. The release focuses on eliminating the last runtime and
observability defects so AIOS can run real goals end-to-end against a live
gateway without manual intervention.

## What Changed

### Step sync fix (P0 — critical visibility bug)
The executor populated `goal.context["workflow_result"]["step_results"]` but
never updated `Goal.steps`, so every goal reported `0/N completed` with all
steps `pending` — even when work had executed successfully. A new
`_sync_goal_steps()` method keeps the public step records in sync with the
internal result map (ADR-0028).

### Note parsing fix
The planner's `create_note` template was too narrow — common phrasing like
"save a note titled X with body Y" fell through to a generic fallback that
hardcoded the title. The trigger set is now wider (`save|capture|jot|store|keep`
+ plural `notes`), and the offline fallback routes note-like phrases through
`_split_note()` so captured notes carry a real title and body (ADR-0028).

### WebSocket reconnect
`_ws_stream()` now retries with exponential backoff (max 20 retries, capped
30s) instead of failing on the first connection error.

### Stdout flush
All `_watch()` print calls now use `flush=True` so output appears immediately
in pipes and non-TTY contexts.

### Daemon persistence
The daemon now persists goals to disk (`~/.aios/daemon/daemon-state.json`) and
restores them on restart. An `on_goal_update` callback re-saves after each
state change.

### Lint cleanup
Zero lint warnings across `packages/`, `services/`, and `tests/` (pre-existing
`tests/test_browser.py` I001 excluded).

## Upgrade Notes

- No schema/migration changes.
- No breaking API changes.
- Daemon persistence is opt-in via `DaemonConfig.persist` (default off); when
  enabled, goals survive daemon restarts.

## Compliance

- FROZEN interfaces (`Skill*`, `aios.agents.permissions.*`) untouched.
- Suite: **1195 passed, 55 skipped**. Lint clean.
