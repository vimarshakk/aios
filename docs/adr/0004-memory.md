# ADR-0004: Unified Memory Architecture

**Status:** Accepted  
**Date:** 2026-07-17  
**Deciders:** AIOS Core Team

## Problem

AIOS needs persistent memory across sessions with different storage characteristics (short-term cache, long-term vectors, episodic timelines, entity relationships). No single backend fits all use cases.

## Decision

Define `MemoryBackend` as the abstract interface for all storage backends. Provide 5 implementations (ShortTerm, Episodic, Entity, Cache, LongTerm) managed by `HybridMemoryManager` with weighted retrieval, priority ordering, and lifecycle events.

```python
class MemoryBackend(ABC):
    async def store(content: str, *, metadata: dict | None) -> str: ...
    async def retrieve(query: str, *, top_k: int = 5, min_score: float = 0.0) -> list[RetrievalResult]: ...
    async def delete(doc_id: str) -> bool: ...
    async def clear() -> None: ...
    async def count() -> int: ...
```

## Rationale

- **Polymorphic storage:** Each backend optimizes for its access pattern (recency, relationships, vectors, TTL).
- **Unified retrieval:** `HybridMemoryManager.retrieve()` queries all enabled backends, merges results by weight × score, deduplicates, and returns a single ranked list.
- **Lifecycle events:** `MemoryEvent` enables observability (store/retrieve/delete notifications).
- **Backend independence:** Backends don't know about each other. The manager orchestrates.

## Alternatives Considered

1. **Single vector store (ChromaDB/Pinecone):** Rejected — doesn't support entity relationships or time-range queries.
2. **Custom ORM over PostgreSQL:** Rejected — over-engineered for M1. Vector search needs a dedicated backend.
3. **File-based memory:** Rejected — no query capability, poor concurrency.

## Consequences

- `RetrievalResult` is the universal return type for all memory queries.
- Backends use keyword-only `retrieve()` args (enforced by `ARG002` noqa pattern).
- `HybridMemoryManager` is the only class agents and context builders interact with.
- `MemoryBackend.close()` is async to support HTTP-based backends.

## Future Evolution

- M2: PostgreSQL + pgvector backend for production deployment.
- M2: Memory consolidation (merge duplicate entries, compress old episodic memories).
- M3: Distributed memory (cross-device sync via ABDM or custom protocol).
