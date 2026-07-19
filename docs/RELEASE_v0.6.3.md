# AIOS v0.6.3 — Autonomous Planner & Native Goal Runner (M6)

**Release date:** 2025-07-18
**Type:** Minor (autonomy layer)
**Supersedes:** v0.6.2 (native browser skill, ADR-0023)

## Summary

M6 delivers the **autonomy layer**: AIOS can now turn a natural-language
objective into a validated, typed task graph (DAG) and execute it through the
native skills — no manual skill listing required. Planning is
**deterministic-first**: known intents are handled by offline templates; a
(recommended) LLM fallback handles novel goals. Every step resolves through the
`CapabilityResolver` (native-first) and runs as a native skill, with human
approval gates for sensitive operations.

The planned graph, per-step lifecycle events, and the workflow result are
persisted on the `Goal` and streamed over the existing `/goals` WebSocket, so
progress survives daemon restarts.

## What's New

- `services/supervisor/src/aios/supervisor/task_graph.py`: `Task`, `TaskGraph`,
  `validate_task_graph` (unique ids, known deps, cycle detection, serialization).
- `services/supervisor/src/aios/supervisor/planner.py`: `AutonomousPlanner`
  deterministic-first hybrid — 6 intent templates (`hackernews`, `open`,
  `commit`, `docker`, `create_note`, `summarize`), the `summarize` pipeline
  (`browser` → `llm.summarize` → `notes` → `notify`), optional LLM fallback
  with strict JSON schema + fence parsing, and a safe offline fallback.
- `services/supervisor/src/aios/supervisor/executor.py`: `NativeGoalRunner`
  bridges the planner's DAG to `aios.workflows.WorkflowExecutor`; each
  `tool_call` step resolves the capability (`platform.resolve`) and executes
  (`platform.execute_skill`). Pre-flight approval gate for `external:` /
  `destructive:` / `publish:` capabilities → `GoalStatus.WAITING_APPROVAL`.
- `Supervisor` wiring: `submit()` now plans + runs via `AutonomousPlanner` +
  `NativeGoalRunner` (accepts `llm_fn`, `planner_timeout_seconds`); `resume()`
  reuses the persisted `task_graph`.
- `Goal.to_dict()` enriched with `task_graph`, `events`, and `workflow_result`.
- `services/supervisor/tests/test_m6_planner.py`: 10 planner/executor tests.
- Legacy `tests/test_supervisor.py` + `tests/test_daemon_briefing.py` migrated
  to the M6 contract (fake platform with `resolve` + async `execute_skill` +
  `create_workspace`).

## Examples

- `aios "Summarize Hacker News"` → browse → summarize → write note → notify.
- `aios "open example.com"` → `browser.open` via native `BrowserSkill`.
- `aios "commit my changes"` → `git.status` → `git.commit`.
- `aios "delete my Downloads folder"` → paused at `WAITING_APPROVAL`
  (destructive capability, no approver).

## Compliance

- FROZEN interfaces (`Skill`, `SkillManifest`, `SkillContext`, `SkillResult`,
  `SkillStatus`, `aios.agents.permissions.*`) unchanged.
- Native-first preserved: every step routes through `CapabilityResolver`.
- Test suite: **1159 passed, 55 skipped**. Ruff clean (`packages/`, `services/`,
  `tests/`; pre-existing `tests/test_browser.py` I001 excluded).

## Deferred to M6.1

Parallel execution, automatic retries, and plan reflection/self-correction. The
`WorkflowExecutor` already supports retry/condition routing; the planner/runner
leave explicit hooks for these.

## Related

- ADR-0024 (this release)
- ADR-0022 (native-first capability resolution), ADR-0023 (daemon + briefings)
