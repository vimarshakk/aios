# ADR-0024: Autonomous Planner & Native Goal Runner (M6)

**Status:** Accepted
**Date:** 2025-07-18
**Supersedes:** ADR-0023 (AIOS daemon + briefings)
**Superseded by:** —

## Context

M1–M5 delivered native execution (CapabilityResolver, 7 native skills, gateway
`/goals` REST+WS, `aios` CLI, daemon, briefings). Until M6, a goal was a flat
list of skills executed sequentially by the Supervisor. There was **no
decomposition of a natural-language objective into a validated, ordered task
graph**, and no LLM-assisted planning. AIOS could not turn "summarize Hacker
News and email me the notes" into a real plan.

We need autonomy: objective → validated typed DAG → executed through native
skills via the CapabilityResolver, with human approval gates for sensitive
operations. This is the AIOS autonomy layer.

## Decision

Introduce three new modules in `aios.supervisor`:

1. **`task_graph.py`** — canonical `Task` / `TaskGraph` model.
   - `Task`: `id`, `capability`, `action`, `inputs`, `depends_on`,
     `expected_output`.
   - `validate_task_graph`: unique ids, every `depends_on` references a known
     task, no cycles, every capability is non-empty. Returns `list[str]` errors
     so callers can surface them. Serializable via `to_dict` / `from_dict`.

2. **`planner.py`** — `AutonomousPlanner` (deterministic-first hybrid).
   - Templates map known intents → `TaskGraph` (e.g. `hackernews`,
     `open`, `commit`, `docker`, `create_note`, `summarize`). Templates never
     call the network/LLM.
   - `summarize` is a multi-step pipeline: `browser` → `llm.summarize` →
     `notes` → `notify`, with dependency edges.
   - **LLM fallback**: if an `llm_fn` is supplied and no template matches, the
     planner asks the model for a JSON task list (with a strict schema +
     few-shot), parses it with fence-stripping (`_parse_llm_tasks`), and
     validates. Offline (no `llm_fn`) falls back to a safe single-step
     `browser.open` pipeline.
   - `plan_async(goal, capabilities=None) -> TaskGraph`.

3. **`executor.py`** — `NativeGoalRunner`.
   - `build_graph` → `planner.plan_async` → `validate_task_graph`.
   - `execute(goal, graph, *, workspace_id)`: converts the graph to a
     `aios.workflows.Workflow`, runs it through `WorkflowExecutor` (topological
     ready-set, event bus), where each `tool_call` step resolves the capability
     (`platform.resolve`) and executes (`platform.execute_skill`).
   - **Approval gate**: a pre-flight pass raises `ApprovalRequiredError` for any
     step whose capability starts with `external:` / `destructive:` /
     `publish:` when `require_approval` is set and there is no approver
     callback — the Supervisor maps this to `GoalStatus.WAITING_APPROVAL`.
   - Persists `task_graph`, per-step `events`, and `workflow_result` onto
     `Goal.context` (surfaced via `Goal.to_dict()` → WebSocket).

`Supervisor` wiring: `submit()` plans via `AutonomousPlanner` + `NativeGoalRunner`
(now also accepts `llm_fn` and `planner_timeout_seconds`). `resume()` reuses the
persisted `task_graph` so progress survives daemon restarts. The legacy
sequential `_run` / `_execute_step` / `platform.plan()→SkillPlan` path is
removed.

**Core M6 is sequential.** Parallelism, retries, and reflection are deferred to
M6.1 (the `WorkflowExecutor` already supports retries/condition routing; the
planner/runner leave hooks for them).

## Consequences

- **Frozen contracts preserved**: `Skill` / `SkillManifest` / `SkillContext` /
  `SkillResult` / `SkillStatus`, and `aios.agents.permissions.*` are untouched.
- **Deterministic-first**: known intents are fast, offline, and reproducible;
  LLM is only a fallback for truly novel goals and is fully optional.
- **Native-first**: every step goes through the `CapabilityResolver`, keeping
  the M5 guarantee that native skills are preferred over external providers.
- **Observability**: step lifecycle events and the planned graph are part of
  goal state, available through the existing `/goals` WebSocket.
- **Test surface**: 10 new planner/executor tests + 5 migrated supervisor/
  daemon-briefing tests (1159 passed, 55 skipped; lint clean).

## Alternatives Considered

- *Keep flat skill lists, add LLM only.* Rejected — no dependency modeling, no
  reuse of `WorkflowExecutor`, no validation.
- *Execute planner output as arbitrary Python.* Rejected — violates the
  native-first / sandbox posture and the frozen `Skill` contract.
- *Always use the LLM.* Rejected — non-deterministic, offline-incompatible, and
  unnecessary for the 6 templated intents that cover the majority of goals.
