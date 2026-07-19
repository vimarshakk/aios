# ADR-0028: Goal step-result synchronisation & planner note parsing

- **Status:** Accepted
- **Date:** 2025-07-18
- **Supersedes:** — (stabilization fix, no prior decision)
- **Superseded by:** —

## Context

During the v0.7.0 stabilization sprint, a real CLI smoke test against a live
gateway revealed two defects that unit tests missed because the unit harness
calls `NativeGoalRunner.execute()` directly and asserts on
`goal.context["workflow_result"]["step_results"]`.

1. **Step-record desync.** The executor populated
   `goal.context["workflow_result"]["step_results"]` (keyed by task id) but never
   updated `goal.steps`, the `list[StepRecord]` that the gateway serialises for
   the REST API, WebSocket stream, and CLI. Every `aios run` therefore
   reported `0/N completed` with all steps `pending`, even though the work had
   actually executed and succeeded. This is a **critical visibility bug**: a
   user cannot tell whether their goal ran.

2. **Note title/body loss.** The planner's `create_note` template was only
   triggered by `create|write|make|add` immediately before `note|memo`. The very
   common phrasing `save a note titled X with body Y` fell through to
   `_local_fallback`, which hardcoded the title `"Captured goal"` and stored the
   raw objective as the body — producing useless notes.

## Decision

- The executor is the single owner of step execution and **must** keep the
  public `Goal.steps` records in sync with the internal `step_results` map. Add
  `NativeGoalRunner._sync_goal_steps()` called at the end of `execute()`,
  mapping each `StepRecord` to its task by capability and copying
  `status`/`error`/`result`/`attempts`/`finished_at`.
- The planner's `create_note` trigger is widened to include
  `save|capture|jot|store|keep` and the plural `notes`. The offline
  `_local_fallback` now routes any note-like phrase through `_split_note()` so
  captured notes carry a real title and body.

## Consequences

- **Positive:** REST/WS/CLI now reflect true per-step progress and outcomes.
  Notes created via natural phrasing are correctly titled and summarised.
- **Positive:** The fix is local to the executor/planner; the frozen interfaces
  (`Permission*`, `Skill*`) are untouched.
- **Negative:** none — `_sync_goal_steps` is defensive (skips unmatched records)
  and adds negligible overhead.

## References

- `services/supervisor/src/aios/supervisor/executor.py` — `_sync_goal_steps`
- `services/supervisor/src/aios/supervisor/planner.py` — `create_note` template,
  `_local_fallback`, `_split_note`
- `docs/RELEASE_v0.7.0.md`
