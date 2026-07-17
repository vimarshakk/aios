# ADR-0009: Gateway + SDK — HTTP API and CLI

**Status:** Accepted  
**Date:** 2026-07-17  
**Deciders:** AIOS Core Team

## Problem

AIOS needs a network-accessible API for desktop/mobile/web clients and a command-line interface for developers. The gateway must route requests to the orchestrator and expose system status.

## Decision

Implement:
- **FastAPI Gateway** with REST endpoints (`/chat`, `/health`, `/agents`, `/tools`) and WebSocket (`/ws/chat`)
- **AiosClient** Python SDK with async httpx, injectable HTTP client, session management
- **typer CLI** with commands: `chat`, `agent`, `tool`, `provider`, `status`, `config`

```python
# Gateway
@app.post("/chat") async def chat(req: ChatRequest) -> ChatResponse: ...
@app.get("/health") async def health() -> HealthResponse: ...
@app.websocket("/ws/chat") async def ws_chat(websocket): ...

# SDK
client = AiosClient("http://localhost:8080")
result = await client.chat("Hello", agent="default")

# CLI
aios chat "What's the weather?"
aios agent list
aios status
```

## Rationale

- **FastAPI:** Async-native, auto-generates OpenAPI docs, Pydantic validation.
- **Orchestrator delegation:** Gateway is thin — all business logic lives in `Orchestrator.route()`.
- **SDK injectability:** `AiosClient(http_client=httpx_client)` enables testing without HTTP.
- **typer + rich:** Modern CLI with auto-generated help, colored output, table formatting.

## Alternatives Considered

1. **gRPC:** Rejected for M1 — REST is simpler for initial integration. gRPC could be added as an alternative transport in M2.
2. **Flask:** Rejected — sync-only, no native WebSocket, no async support.
3. **Click (without typer):** Rejected — typer provides type-safe CLI with less boilerplate.
4. **GraphQL:** Deferred — REST is sufficient for M1. GraphQL could be added in M2 for flexible querying.

## Consequences

- Gateway binds to `AIOS_GATEWAY_PORT` (default 8080). CORS allows all origins for development.
- `ChatRequest.context` field exists but is unused in M1 — reserved for future context injection.
- SDK `AiosClient` creates a new httpx client per request by default. Pass `http_client` for connection pooling.
- CLI commands hit the gateway HTTP API — they require a running gateway.

## Future Evolution

- M2: Authentication (JWT/API keys) on gateway endpoints.
- M2: Rate limiting and request queuing.
- M3: GraphQL endpoint for flexible queries.
- M3: SDK published to PyPI with semantic versioning.
