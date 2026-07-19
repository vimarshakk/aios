# ADR-0003: Context Engine — Retrieval-Augmented Assembly

**Status:** Accepted  
**Date:** 2026-07-17  
**Deciders:** AIOS Core Team

## Problem

LLMs need context assembled from multiple sources (system prompt, conversation history, memory retrieval) within a token budget. No existing AIOS component handles this assembly.

## Decision

Create a `ContextBuilder` that assembles messages from multiple sources in a deterministic pipeline:

1. System prompt (always first)
2. Memory retrieval (from `HybridMemoryManager`)
3. Relevance ranking (optional)
4. Conversation summarization (when token budget exceeded)
5. Sliding window (keep recent messages)
6. User query (always last)

```python
class ContextBuilder:
    async def build(spec: ContextSpec) -> BuildResult: ...
    async def build_simple(query, *, system_prompt, conversation, max_context_tokens) -> list[Message]: ...
```

## Rationale

- **Separation of concerns:** Memory retrieval, ranking, summarization, and windowing are independent concerns composed by the builder.
- **Token-aware:** `ContextSpec.max_context_tokens` drives summarization and windowing decisions.
- **Pluggable components:** Each stage (retriever, ranker, summarizer, window) is independently replaceable.
- **Two APIs:** `build()` for full control, `build_simple()` for quick integration.

## Alternatives Considered

1. **Monolithic context assembler:** Rejected — harder to test and extend individual stages.
2. **LLM-driven context selection:** Rejected for M1 — expensive and non-deterministic. Could be added in M2 as a ranker strategy.
3. **No context engine (raw concatenation):** Rejected — leads to context overflow and poor relevance.

## Consequences

- `ContextBuilder` depends on `MemoryBackend` and `HybridMemoryManager` — clean dependency direction (context → memory, not reverse).
- `BuildResult` carries metadata (`was_summarized`, `memory_used`) for observability.
- `LLMFn` type alias enables summarization without hard-coding a provider.

## Future Evolution

- M2: Reranking via cross-encoder models.
- M2: Context caching (don't re-retrieve for repeated queries).
- M3: Multi-modal context (images, tables, code blocks with syntax highlighting).
