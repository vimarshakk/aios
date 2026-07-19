# ADR-0001: Event-Driven Runtime

**Status:** Accepted  
**Date:** 2026-07-17  
**Deciders:** AIOS Core Team

## Problem

AIOS subsystems (providers, memory, agents, plugins, workflows) need to communicate without creating circular dependencies or tight coupling. Cross-cutting concerns (logging, metrics, audit) need hook points without modifying every module.

## Decision

Adopt a synchronous, thread-safe `EventBus` with typed events. The bus is a process-wide singleton with optional history recording.

```python
class EventBus:
    def subscribe(event_type: EventType, callback: Subscriber) -> None: ...
    def unsubscribe(event_type: EventType, callback: Subscriber) -> None: ...
    def publish(event_type: EventType, data: dict | None = None) -> Event: ...
    @property
    def history(self) -> list[Event]: ...

# Module-level singleton
def get_event_bus(*, record_history: bool = False) -> EventBus: ...
def reset_event_bus() -> None: ...
```

`EventType` is a `StrEnum` with values like `INFERENCE_START`, `TOOL_CALL_END`, `MEMORY_STORE`, `AGENT_TURN_START`, `WORKFLOW_START`, `SESSION_START`, etc.

## Rationale

- **Decoupling:** Publishers and subscribers have no knowledge of each other. Systems communicate through events, not direct calls.
- **Observability:** History recording enables agent timelines, tool latency tracking, and debugging without instrumenting every module.
- **Thread safety:** `threading.Lock` protects subscriber lists. Safe for mixed sync/async environments.
- **Simplicity:** Synchronous dispatch avoids async coordination complexity. Events are fire-and-forget.

## Alternatives Considered

1. **Async event bus (asyncio.Queue):** Rejected — adds event loop dependency, complicates testing, and synchronous dispatch is sufficient for M1 scale.
2. **Message broker (RabbitMQ, Redis Streams):** Over-engineered for in-process communication. Could be adopted for inter-service events in M3.
3. **Observer pattern without central bus:** Creates point-to-point coupling. Central bus is simpler to reason about.
4. **Signal libraries (blinker):** External dependency for functionality that fits in ~80 lines of code.

## Consequences

- All subsystems can communicate without direct imports.
- `EventBus` is the single coordination point — easy to instrument, debug, and replace.
- History recording is opt-in to avoid memory pressure in production.
- Subscribers must handle exceptions — a failing subscriber does not block the bus.
- `reset_event_bus()` exists for test isolation.

## Future Evolution

- M2: Async event dispatch for long-running handlers.
- M2: Event filtering and wildcard subscriptions.
- M3: Inter-service events via message broker (RabbitMQ/Redis) behind the same EventBus API.
- M3: Event replay for workflow recovery.
