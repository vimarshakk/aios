# ADR-0001: Event-Driven Runtime

**Status:** Accepted  
**Date:** 2026-07-17  
**Deciders:** AIOS Core Team

## Problem

AIOS needs a decoupled communication mechanism between subsystems (providers, memory, agents, plugins, workflows) without creating circular dependencies or tight coupling.

## Decision

Adopt a synchronous, thread-safe EventBus pattern with typed events. The EventBus is a singleton (module-level lazy init) that supports subscribe/unsubscribe/publish. Events carry a `EventType` enum and arbitrary `dict` data.

```python
class EventBus:
    def subscribe(self, event_type: EventType, callback: Subscriber) -> None: ...
    def unsubscribe(self, event_type: EventType, callback: Subscriber) -> None: ...
    def publish(self, event_type: EventType, data: dict | None = None) -> Event: ...
```

## Rationale

- **Decoupling:** Publishers don't know about subscribers. Subscribers register interest by event type.
- **Simplicity:** Synchronous dispatch avoids async coordination complexity. Events are fire-and-forget.
- **Thread safety:** `threading.Lock` protects subscriber lists. Safe for mixed sync/async contexts.
- **Observability:** Optional `record_history=True` enables debugging and audit trails.

## Alternatives Considered

1. **Async EventBus (asyncio.Queue):** Rejected — adds event loop dependency, complicates testing, and synchronous dispatch is sufficient for M1 scale.
2. **Message broker (RabbitMQ/Redis Streams):** Rejected for M1 — over-engineered for in-process communication. Could be adopted for inter-service events in M2.
3. **Observer pattern without central bus:** Rejected — creates point-to-point coupling. Central bus is simpler to reason about.

## Consequences

- All subsystems can communicate without direct imports.
- Event types are extensible via `EventType` enum (StrEnum).
- Subscribers must handle exceptions themselves — a failing subscriber does not block the bus.
- History recording is opt-in to avoid memory pressure in production.

## Future Evolution

- M2: Consider async event dispatch for long-running handlers.
- M2: Event filtering and wildcard subscriptions.
- M3: Inter-service events via message broker (RabbitMQ/Redis) as a transport layer behind the same EventBus API.
