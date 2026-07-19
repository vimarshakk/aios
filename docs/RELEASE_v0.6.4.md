# AIOS v0.6.4 — M6.1: Parallel Execution, Retry Policies & Reflection

**Release date:** 2025-07-18
**Type:** Minor (autonomy hardening)
**Supersedes:** v0.6.3 (core M6 planner + runner, ADR-0024)

## Summary

M6.1 makes the autonomous pipeline **robust and concurrent** without changing
the architecture or the frozen contracts. A single topological scheduler in
`NativeGoalRunner` now adds three capabilities that separate an autonomous
agent from a scripted workflow runner:

- **Parallel execution** — independent ready-set tasks run concurrently
  (`asyncio.gather`); dependencies still wait. A `parallel` flag toggles this.
- **Retry policies** — `Task.retry = {"max_retries", "backoff_seconds"}`; the
  planner auto-injects a bounded retry onto `browser.` / `git.` / `docker.`
  steps. Failed attempts emit `retry` events and self-heal.
- **Reflection / dynamic replanning** — an optional `reflection_fn(task,
  output, graph)` hook fires after each reflected step and may mutate the live
  graph (swap a capability, append a discovered step). Injected tasks run in
  the same execution because the scheduler re-reads the graph each iteration.

The planned graph is re-snapshotted at the end of execution so reflection-
injected steps persist on the goal and stream over the `/goals` WebSocket.

## What Changed

- `services/supervisor/src/aios/supervisor/task_graph.py`: `Task` gains
  `retry: dict | None` and `reflect: bool` (serialised in `to_dict`/`from_dict`).
- `services/supervisor/src/aios/supervisor/planner.py`: `AutonomousPlanner`
  injects `retry` onto network/IO-prone capabilities via `_apply_defaults`.
- `services/supervisor/src/aios/supervisor/executor.py`: `NativeGoalRunner`
  gains a parallel topological scheduler with retry + reflection; `parallel`
  and `reflection_fn` constructor options; richer `workflow_result` (status,
  per-step results, `parallel` flag) and per-step lifecycle `events`.
- `services/supervisor/src/aios/supervisor/supervisor.py`: `Supervisor` exposes
  `parallel` and `reflection_fn`; legacy `max_step_attempts` retained for
  compatibility.
- `services/supervisor/tests/test_m6_planner.py`: +4 M6.1 tests.
- `tests/test_daemon_briefing.py`: `test_daemon_resume_runs_goal` migrated to a
  single event loop so the resumed goal reaches a terminal state.

## Examples

- `aios "open example.com and check my git status"` → `browser.open` and
  `git.status` run **concurrently**, then `notify` runs once both finish.
- A flaky `browser.open` retries up to 2× with 0.2s backoff before failing.
- A reflection hook can swap a failed capability or append a follow-up step
  mid-run (dynamic replanning).

## Compliance

- FROZEN interfaces (`Skill`, `SkillManifest`, `SkillContext`, `SkillResult`,
  `SkillStatus`, `aios.agents.permissions.*`) unchanged.
- Native-first routing preserved via `CapabilityResolver`.
- Suite: **1159 passed, 55 skipped**. Ruff clean (`packages/`, `services/`,
  `tests/`; pre-existing `tests/test_browser.py` I001 excluded).

## Deferred

Long-term memory and multi-agent coordination (the natural next extensions of
the reflection hook).

## Related

- ADR-0025 (this release), ADR-0024 (core M6)
