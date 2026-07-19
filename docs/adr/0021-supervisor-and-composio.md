# ADR-0021: Supervisor Service & Composio Consumption

**Date:** 2025-07-18
**Status:** Accepted
**Deciders:** Core team

## Context

M1–M4 built the AIOS platform primitives (agents, skills, orchestrator,
connectors, integrations, capability catalog, policy, workspaces, artifacts).
These are excellent *capabilities* but there is no top-level service that owns
**long-running autonomous goal execution** on behalf of a user. The AIOS Desktop
experience needs exactly that: a user states an objective, and the system
plans, schedules, executes, verifies, and reports — with pause/resume, approval
gating, and retry.

Two design questions:

1. **Do we build a new orchestration engine?** No. `DeveloperPlatform` already
   composes the planner (`SkillPlanner`), skills (`SkillRegistry`/`SkillExecutor`),
   policy (`PolicyEngine`), connectors (`ConnectorRegistry`), workspaces, and
   artifacts. Reinventing execution would duplicate ADR-0019 layering.
2. **Do we build first-party connectors for every SaaS app (GitHub/Notion/Gmail/
   Slack/Linear/…)?** No. Composio already maintains managed OAuth and a huge
   tool catalog. Reimplementing that integration surface is wasted effort and a
   maintenance liability.

## Decision

### Supervisor (`services/supervisor`)
Add a new top-level service, `aios-supervisor`, that is the **composition root**
for autonomous goals. It does not implement planning, scheduling, skills,
permissions, or connectors — it *orchestrates* the existing `DeveloperPlatform`:

```
User → Supervisor → Planner (SkillPlan)
     → Task Graph (plan.steps)
     → Skill Scheduler (DeveloperPlatform.execute_skill, policy-gated)
     → Connectors (Composio + first-party via skills)
     → Verification (SkillResult / policy)
     → Memory (workspace artifacts + execution history)
     → Response
```

The Supervisor adds **only** goal-lifecycle concerns:
- `Goal` / `GoalStatus` / `StepRecord` state model (`goal.py`).
- Submission plans via `platform.plan()` and schedules steps as a background
  task graph.
- **Approval gate**: steps whose skill declares a capability with an
  `external:` / `destructive:` / `publish:` prefix pause for human approval
  (via an optional `approval_callback`, or halt in `WAITING_APPROVAL` and await
  `resume()`).
- **Retries**: per-step `max_step_attempts`; a failed step reverts to `PENDING`
  and the goal pauses so a later `resume()` retries.
- **Pause / resume / cancel**: control methods mutate goal state; the run loop
  re-checks state between steps so it can stop and be restarted cleanly.
- A thin `main.run()` keeps the service self-runnable; the M5 desktop drives it
  over the gateway transport.

### Composio Consumption (`packages/integrations`)
Add `ComposioConnector` + `ComposioIntegration` under
`aios.integrations.composio`:
- `ComposioIntegration` is the thin **transport** that maps a Composio tool slug
  onto `composio.tools.execute`. It conforms to the frozen `Integration` ABC.
- `ComposioConnector` conforms to the frozen `Connector` ABC. It exposes **curated
  bindings** for the common SaaS apps (GitHub/Notion/Gmail/Slack/Linear) so they
  are catalog-visible, **and** supports discovery-driven, dynamic execution via
  `invoke(capability, perms, action=<COMPOSIO_SLUG>)`.
- `composio` is an **optional, heavy dependency** imported lazily. Without the
  SDK, the connector constructs fine but raises a clear `ImportError` on use.
- Wired into `register_builtin_connectors` under the `composio` integration key
  (gated on SDK availability).

### Platform extension
`DeveloperPlatform.capabilities_for_skill(name)` is added — a read-only helper
that returns the capability ids declared by a registered skill's manifest. It is
the minimal seam the Supervisor needs to decide approval gating without reaching
into catalog internals.

## Consequences

- AIOS can drive long-running goals through one service instead of wiring
  planners/executors itself.
- The SaaS integration surface is essentially "free" via Composio; we only
  maintain curated bindings and the transport adapter.
- Optional `composio` dependency keeps the rest of AIOS import-clean and
  installable without the heavy SDK.
- The Supervisor never bypasses the frozen `Permission`/`PermissionSet` or the
  `PolicyEngine`; it gates every step through `platform.capabilities_for_skill`
  + the approval prefixes.

## Alternatives considered

- **Build first-party SaaS connectors**: rejected — duplicates Composio's
  managed OAuth and tool maintenance.
- **New workflow engine inside Supervisor**: rejected — `DeveloperPlatform`
  already composes planner/executor/policy/connectors (ADR-0019). Supervisor is
  coordination, not reimplementation.
