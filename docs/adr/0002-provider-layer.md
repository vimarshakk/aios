# ADR-0001: InferenceEngine as the Provider Abstraction

**Status:** Accepted  
**Date:** 2026-07-17  
**Deciders:** AIOS Core Team

## Problem

AIOS needs to support multiple LLM providers (Ollama, OpenAI, Anthropic, Gemini, local models) without coupling agent logic to any specific provider SDK or API.

## Decision

Define `InferenceEngine` as the abstract base class for all LLM providers. Every provider implements `complete()`, `stream()`, `health()`, `models()`, and `close()`. An `EngineRegistry` maps string names to engine instances. An `EngineFactory` (`create_engine()`) resolves engines by name.

```python
class InferenceEngine(ABC):
    name: str = "base"
    async def complete(messages, *, model, temperature, max_tokens, stop, **kwargs) -> CompletionResult: ...
    async def stream(messages, *, model, temperature, max_tokens, stop, **kwargs) -> AsyncIterator[StreamChunk]: ...
    async def health() -> bool: ...
    def models() -> list[str]: ...
    async def close() -> None: ...
```

## Rationale

- **Uniform interface:** Agents, workflows, and plugins don't care which provider backs the engine.
- **Registry pattern:** Dynamic discovery. New providers register via `@EngineRegistry.register("name")`.
- **Streaming as first-class:** `stream()` returns `AsyncIterator[StreamChunk]`, enabling real-time token delivery.
- **Health checks:** `health()` enables runtime provider validation without catching exceptions.

## Alternatives Considered

1. **Direct SDK usage per provider:** Rejected — forces every consumer to handle provider-specific APIs.
2. **LiteLLM as universal adapter:** Considered but rejected — adds a dependency with its own abstraction layer. We prefer our own thin abstraction.
3. **Provider-per-model (no engine abstraction):** Rejected — conflates model selection with provider selection.

## Consequences

- Adding a new provider requires: implement `InferenceEngine`, register with `@EngineRegistry.register()`, write tests.
- `CompletionResult`, `Usage`, and `StreamChunk` are the shared data contracts for all responses.
- Provider-specific features (tool calling, vision) are exposed via `**kwargs` — typed extensions come in M2.

## Future Evolution

- M2: `LLMProvider`, `EmbeddingProvider`, `STTProvider`, `TTSProvider`, `VisionProvider` as specialized sub-interfaces.
- M2: Provider capability negotiation (e.g., "does this engine support tool calling?").
- M3: Streaming backpressure and chunked WebSocket delivery.
