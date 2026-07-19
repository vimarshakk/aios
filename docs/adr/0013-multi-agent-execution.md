# ADR-0013: Multi-Agent Execution Architecture

**Date:** 2025-07-17
**Status:** Accepted
**Deciders:** Core team

## Context

M1 had a single-agent event loop. M2 introduced multi-agent execution with concurrent task processing, priority queues, worker pools, retry policies, and dead letter queues. This enables multiple agents to process tasks simultaneously with isolation and fault tolerance.

## Decision

The multi-agent execution system consists of:

- **TaskMessage:** Immutable task payload with priority, TTL, retry count, metadata
- **PriorityQueue:** Per-priority-level async queues (CRITICAL=0, HIGH=1, NORMAL=5, LOW=9, BACKGROUND=15)
- **InMemoryQueue:** Multi-queue system with push/pop/ack/nack/peek
- **Worker:** Processes tasks from queues, registered per task_type
- **WorkerPool:** Manages N workers with load balancing and lifecycle
- **RetryPolicy:** Configurable retry with backoff, jitter, non-retryable exceptions
- **DeadLetterQueue:** Captures permanently failed tasks with error metadata
- **TaskPersistence:** File-system snapshots for task state recovery

## Consequences

- Workers register handlers for specific task types: `worker.register("email", handler)`
- Tasks are ack'd after successful processing; nack triggers retry
- Retry policy checks `non_retryable_exceptions` before retrying (empty tuple means all retryable)
- Dead letter queue has configurable max size (default 10,000)
- Persistence snapshots tasks to disk for crash recovery
- Worker stats are a property (dict), not a method

## Key Design Decisions

1. **Priority as IntEnum:** CRITICAL=0, not a string — enables natural ordering
2. **TTL <= 0 means no expiration:** Consistent with time-based semantics
3. **Worker handlers are async:** Must support I/O-bound tasks
4. **Queue operations are async:** Non-blocking even for in-memory queues
5. **Dead letter entries include stacktrace:** Essential for debugging failed tasks

## Alternatives Considered

1. **Redis-backed queues:** Better for distributed but adds infra dependency
2. **Celery/RQ:** Overkill; we need lightweight in-process execution
3. **Actor model:** Interesting but adds complexity without clear benefit

## References

- `packages/core/src/aios/core/distributed/queue.py`
- `packages/core/src/aios/core/distributed/worker.py`
- `packages/core/src/aios/core/distributed/pool.py`
- `tests/test_distributed.py`
