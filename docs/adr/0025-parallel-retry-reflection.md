# ADR-0025: M6.1 — Parallel Execution, Retry Policies & Reflection

**Status:** Accepted
**Date:** 2025-07-18
**Supersedes:** ADR-0024 (core M6 autonomous planner)
**Superseded by:** —

## Context

Core M6 delivered deterministic-first planning and a sequential native
executor. The pipeline was correct but limited:

- Every task ran **one at a time**, even independent leaves of the DAG.
- A transient failure (flaky network, momentary lock) failed the whole goal.
- The planner had **no feedback loop** — a failed step could not trigger a
  self-correction or a dynamic addition to the plan.

These three gaps are what separate a scripted workflow runner from an
autonomous agent. M6.1 closes them without changing the frozen contracts or
the native-first guarantee.

## Decision

Extend `NativeGoalRunner` (in `aios.supervisor.executor`) with a single
topological scheduler that adds three capabilities:

1. **Parallel execution.** Each scheduling iteration computes the
   dependency-ready set and runs all ready tasks **concurrently** via
   `asyncio.gather`. Dependencies still wait for predecessors. A `parallel`
   flag (default `True`) selects concurrent vs. sequential dispatch.

2. **Retry policies.** `Task` gains an optional `retry` field
   (`{"max_retries": n, "backoff_seconds": s}`). The runner retries a failed
   task up to `n` times with `s` seconds of backoff between attempts, emitting
   `retry` lifecycle events. The `AutonomousPlanner` injects a bounded
   retry-with-backoff (`max_retries: 2`, `backoff: 0.2s`) onto
   network/IO-prone capabilities (`browser.`, `git.`, `docker.`).

3. **Reflection / dynamic replanning.** `Task.reflect` (default `True`) and an
   optional `reflection_fn(task, output, graph)` hook. After each reflected
   step completes, the hook is invoked and may **mutate the live graph** —
   e.g. swap a failed capability, append a newly-discovered step, or refine
   inputs. The scheduler re-reads `graph.tasks` each iteration, so injected
   tasks execute. Reflection errors are caught and logged so they never break
   execution.

Persistence: the planner's `task_graph` snapshot is refreshed at the end of
`execute()` so dynamically-added steps (from reflection) are visible in
`Goal.context` and streamed over the existing `/goals` WebSocket.

The legacy `WorkflowExecutor`/`Workflow` path is no longer used by the runner
(the new scheduler covers ready-sets, events, and the approval pre-flight),
but `WorkflowExecutor` remains available for condition/approval routing
elsewhere.

## Consequences

- **Faster goals:** independent browser + git + docker leaves now overlap.
- **Robustness:** transient failures self-heal within the retry budget instead
  of failing the goal.
- **Autonomy:** reflection enables self-correction and dynamic replanning (the
  M6.1 "reflection" and "dynamic replanning" goals).
- **Observability:** `retry`/`started`/`completed`/`failed` events are logged
  per step; `workflow_result` records `parallel` and per-step outcomes.
- **Frozen contracts preserved:** `Skill`/`SkillResult`/`SkillStatus`,
  `aios.agents.permissions.*`, and the `CapabilityResolver` are untouched;
  native-first routing is unchanged.
- **Tests:** 4 new M6.1 tests (parallel timing, sequential ordering, retry-then-
  succeed, reflection-driven dynamic replan). Full suite **1159 passed, 55
  skipped**; ruff clean.

## Deferred

Long-term memory (preferred editor/repo/profile) and multi-agent coordination
remain future work; the reflection hook is the natural insertion point for both.
