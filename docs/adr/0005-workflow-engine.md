# ADR-0005: Workflow Engine — DAG-Based Execution

**Status:** Accepted  
**Date:** 2026-07-17  
**Deciders:** AIOS Core Team

## Problem

AIOS needs to execute multi-step tasks (research → analyze → write → review) with dependencies, retries, conditional branching, human approval, and parallel execution. No orchestration mechanism exists.

## Decision

Create a workflow engine with:
- `Workflow` / `WorkflowStep` data types (DAG structure)
- `WorkflowExecutor` (topological execution, handler registration, resume capability)
- `WorkflowPlanner` (LLM-generated or deterministic workflows)
- Supporting modules: state management, retry logic, conditions, approval gates, parallel groups

```python
class Workflow:
    id: str; name: str; steps: list[WorkflowStep]; metadata: dict

class WorkflowStep:
    id: str; type: str; config: dict; dependencies: list[str]

class WorkflowExecutor:
    async def run(workflow: Workflow) -> WorkflowResult: ...
    async def resume(workflow: Workflow, result: WorkflowResult) -> WorkflowResult: ...
```

## Rationale

- **DAG execution:** Dependencies enforce ordering without hard-coding sequence. Steps with satisfied deps execute in parallel batches.
- **Handler registration:** Step types (`tool_call`, `agent_call`, `condition`, `approval`, `parallel`) are extensible via `register_handler()`.
- **Resume capability:** Failed workflows can be resumed from the last successful step via `WorkflowResult.step_results`.
- **Planner integration:** `WorkflowPlanner` generates workflows from natural language descriptions.

## Alternatives Considered

1. **State machines only:** Rejected — insufficient for parallel execution and complex dependency graphs.
2. **Airflow/Prefect:** Rejected — too heavy for in-process orchestration. Could be used for distributed workflows in M3.
3. **Sequential chain only:** Rejected — doesn't support parallelism or conditional branching.

## Consequences

- `WorkflowResult` tracks per-step status, enabling partial execution and resume.
- `StepStatus` enum (PENDING, RUNNING, COMPLETED, FAILED, SKIPPED, WAITING_APPROVAL, BLOCKED) drives UI state.
- Parallel execution is limited to asyncio tasks within a single process.
- Approval steps pause execution and wait for external input.

## Future Evolution

- M2: Persistent workflow state (PostgreSQL-backed) for crash recovery.
- M2: Workflow versioning and rollback.
- M3: Distributed execution (Celery, Dramatiq) for long-running workflows.
