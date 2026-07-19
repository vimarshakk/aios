# ADR-0018: Integrations Platform

**Date:** 2025-07-17
**Status:** Accepted
**Deciders:** Core team

## Context

M3.8 added an integrations platform for connecting to third-party services (GitHub, Slack, email, etc.). The platform provides a unified lifecycle contract for integrations with configuration, connection management, health checks, and execution.

## Decision

Integration framework:

- **Integration base class:** Abstract class with `connect()`, `disconnect()`, `health_check()`, `execute(action, **kwargs)` methods. Lifecycle: `DISCOVERED → CONFIGURED → CONNECTING → CONNECTED → DISCONNECTING → DISABLED`.
- **IntegrationConfig:** Frozen dataclass with name, api_key, base_url, timeout, max_retries, headers, metadata.
- **IntegrationResult:** Frozen dataclass with ok, data, error, status.
- **HealthCheckResult:** Frozen dataclass with healthy, latency_ms, message.
- **IntegrationRegistry:** Manages integration instances — register/unregister, get, by_status, connect_all, disconnect_all, stats.

## Consequences

- Integrations are async — all lifecycle methods are coroutines
- `initialize()` combines configure+connect for convenience
- `shutdown()` combines disconnect+cleanup
- `safe_execute()` auto-reconnects on failure if still configured
- Registry supports connect_all/disconnect_all with per-integration success tracking
- `IntegrationStatus` uses `StrEnum` for easy serialization
- Registry stats return `RegistryStats` dataclass (total/connected/errored/disabled)

## Key Design Decisions

1. **Abstract base class over Protocol:** Easier to enforce lifecycle contract
2. **Frozen dataclasses for results/config:** Immutability prevents accidental mutation
3. **Registry not in DI container:** Simple dict-backed, no overhead
4. **Status enum over string:** Type safety and IDE autocomplete
5. **async lifecycle:** I/O-bound connections need async

## Alternatives Considered

1. **Protocol-based duck typing:** Less enforcement, harder to document
2. **Mixin pattern:** Can't enforce all four lifecycle methods
3. **External framework (e.e. FastAPI dependencies):** Overkill for integration lifecycle

## References

- `packages/integrations/src/aios/integrations/base.py`
- `packages/integrations/src/aios/integrations/types.py`
- `packages/integrations/src/aios/integrations/registry.py`
- `tests/test_integrations.py`
