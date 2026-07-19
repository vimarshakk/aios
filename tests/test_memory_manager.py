"""Tests for HybridMemoryManager and memory events."""

from __future__ import annotations

from typing import Any

import pytest

from aios.memory.backend import MemoryBackend, RetrievalResult
from aios.memory.cache import CacheMemory
from aios.memory.entity import EntityMemory
from aios.memory.episodic import EpisodicMemory
from aios.memory.events import MemoryEvent, MemoryEventType
from aios.memory.manager import HybridMemoryManager
from aios.memory.short_term import ShortTermMemory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TrackingBackend(MemoryBackend):
    """In-memory backend that tracks calls for testing."""

    def __init__(self) -> None:
        self.store_count = 0
        self.retrieve_count = 0
        self.delete_count = 0
        self.clear_count = 0
        self._docs: dict[str, tuple[str, dict[str, Any]]] = {}

    async def store(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        self.store_count += 1
        doc_id = f"doc_{self.store_count}"
        self._docs[doc_id] = (content, metadata or {})
        return doc_id

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[RetrievalResult]:
        self.retrieve_count += 1
        results = []
        for doc_id, (content, meta) in self._docs.items():
            score = 1.0 if query.lower() in content.lower() else 0.1
            if score >= min_score:
                results.append(RetrievalResult(
                    doc_id=doc_id,
                    content=content,
                    score=score,
                    source="tracking",
                    metadata=meta,
                ))
        return results[:top_k]

    async def delete(self, doc_id: str) -> bool:
        self.delete_count += 1
        if doc_id in self._docs:
            del self._docs[doc_id]
            return True
        return False

    async def clear(self) -> None:
        self.clear_count += 1
        self._docs.clear()

    async def count(self) -> int:
        return len(self._docs)

    async def close(self) -> None:
        pass


class FailingBackend(MemoryBackend):
    """Backend that raises on all operations — for resilience testing."""

    async def store(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        raise RuntimeError("boom")

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[RetrievalResult]:
        raise RuntimeError("boom")

    async def delete(self, doc_id: str) -> bool:
        raise RuntimeError("boom")

    async def clear(self) -> None:
        raise RuntimeError("boom")

    async def count(self) -> int:
        raise RuntimeError("boom")

    async def close(self) -> None:
        raise RuntimeError("boom")


# ---------------------------------------------------------------------------
# HybridMemoryManager tests
# ---------------------------------------------------------------------------

class TestHybridMemoryManager:
    """Tests for the HybridMemoryManager facade."""

    @pytest.mark.asyncio
    async def test_register_and_list(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        b2 = CacheMemory()
        mgr.register("tracker", b1)
        mgr.register("cache", b2)
        assert mgr.list_backends() == ["tracker", "cache"]

    @pytest.mark.asyncio
    async def test_unregister(self):
        mgr = HybridMemoryManager()
        mgr.register("a", TrackingBackend())
        assert mgr.unregister("a")
        assert mgr.list_backends() == []
        assert not mgr.unregister("nonexistent")

    @pytest.mark.asyncio
    async def test_enable_disable(self):
        mgr = HybridMemoryManager()
        mgr.register("a", TrackingBackend())
        mgr.disable("a")
        assert not next(cfg for cfg in mgr._backends.values() if cfg.name == "a").enabled
        mgr.enable("a")
        assert next(cfg for cfg in mgr._backends.values() if cfg.name == "a").enabled

    @pytest.mark.asyncio
    async def test_store_to_first_enabled(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        b2 = TrackingBackend()
        mgr.register("a", b1)
        mgr.register("b", b2)
        doc_id = await mgr.store("hello world")
        assert doc_id == "doc_1"
        assert b1.store_count == 1
        assert b2.store_count == 0

    @pytest.mark.asyncio
    async def test_store_to_specific_backend(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        b2 = TrackingBackend()
        mgr.register("a", b1)
        mgr.register("b", b2)
        doc_id = await mgr.store("hello", backend="b")
        assert doc_id == "doc_1"
        assert b1.store_count == 0
        assert b2.store_count == 1

    @pytest.mark.asyncio
    async def test_store_no_backends_raises(self):
        mgr = HybridMemoryManager()
        with pytest.raises(RuntimeError, match="No enabled memory backend"):
            await mgr.store("hello")

    @pytest.mark.asyncio
    async def test_retrieve_merges_results(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        b2 = TrackingBackend()
        mgr.register("a", b1)
        mgr.register("b", b2)
        await b1.store("the quick brown fox")
        await b2.store("lazy brown dog")
        results = await mgr.retrieve("brown")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_retrieve_specific_backends(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        b2 = TrackingBackend()
        mgr.register("a", b1)
        mgr.register("b", b2)
        await b1.store("alpha beta")
        await b2.store("gamma delta")
        results = await mgr.retrieve("alpha", backends=["a"])
        assert len(results) == 1
        assert results[0].content == "alpha beta"
        assert results[0].source == "a"

    @pytest.mark.asyncio
    async def test_retrieve_respects_weight(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        b2 = TrackingBackend()
        mgr.register("a", b1, weight=2.0)
        mgr.register("b", b2, weight=0.5)
        await b1.store("test item")
        await b2.store("test item")
        results = await mgr.retrieve("test")
        assert len(results) == 1  # Deduplicated
        assert results[0].score == 2.0  # a's weight

    @pytest.mark.asyncio
    async def test_retrieve_respects_priority_order(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        b2 = TrackingBackend()
        mgr.register("low", b1, priority=1)
        mgr.register("high", b2, priority=10)
        await b1.store("low priority data")
        await b2.store("high priority data")
        results = await mgr.retrieve("data")
        assert len(results) == 2
        assert results[0].source == "high"

    @pytest.mark.asyncio
    async def test_retrieve_empty_when_all_disabled(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        mgr.register("a", b1)
        mgr.disable("a")
        results = await mgr.retrieve("hello")
        assert results == []

    @pytest.mark.asyncio
    async def test_delete_from_all(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        b2 = TrackingBackend()
        mgr.register("a", b1)
        mgr.register("b", b2)
        await b1.store("data a")
        await b2.store("data b")
        deleted = await mgr.delete("doc_1")
        assert deleted
        assert b1.delete_count == 1
        assert b2.delete_count == 1

    @pytest.mark.asyncio
    async def test_delete_from_specific(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        b2 = TrackingBackend()
        mgr.register("a", b1)
        mgr.register("b", b2)
        await b1.store("a data")
        await b2.store("b data")
        deleted = await mgr.delete("doc_1", backend="a")
        assert deleted
        assert b1.delete_count == 1
        assert b2.delete_count == 0

    @pytest.mark.asyncio
    async def test_clear_all(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        b2 = TrackingBackend()
        mgr.register("a", b1)
        mgr.register("b", b2)
        await b1.store("data")
        await b2.store("data")
        await mgr.clear()
        assert b1.clear_count == 1
        assert b2.clear_count == 1

    @pytest.mark.asyncio
    async def test_clear_specific(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        b2 = TrackingBackend()
        mgr.register("a", b1)
        mgr.register("b", b2)
        await mgr.clear(backend="a")
        assert b1.clear_count == 1
        assert b2.clear_count == 0

    @pytest.mark.asyncio
    async def test_count(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        b2 = TrackingBackend()
        mgr.register("a", b1)
        mgr.register("b", b2)
        await b1.store("x")
        await b1.store("y")
        await b2.store("z")
        counts = await mgr.count()
        assert counts == {"a": 2, "b": 1}

    @pytest.mark.asyncio
    async def test_get_backend(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        mgr.register("a", b1)
        assert mgr.get_backend("a") is b1
        assert mgr.get_backend("nonexistent") is None

    @pytest.mark.asyncio
    async def test_close(self):
        mgr = HybridMemoryManager()
        mgr.register("a", TrackingBackend())
        mgr.register("b", TrackingBackend())
        await mgr.close()

    @pytest.mark.asyncio
    async def test_resilient_to_failing_backend(self):
        mgr = HybridMemoryManager()
        good = TrackingBackend()
        bad = FailingBackend()
        mgr.register("bad", bad)
        mgr.register("good", good)
        await good.store("working")
        results = await mgr.retrieve("working")
        assert len(results) == 1
        assert results[0].content == "working"

    @pytest.mark.asyncio
    async def test_deduplicate_results(self):
        mgr = HybridMemoryManager()
        b1 = TrackingBackend()
        b2 = TrackingBackend()
        mgr.register("a", b1)
        mgr.register("b", b2)
        await b1.store("the quick brown fox")
        await b2.store("the quick brown fox")
        results = await mgr.retrieve("fox")
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Memory events tests
# ---------------------------------------------------------------------------

class TestMemoryEvents:
    """Tests for memory lifecycle events."""

    @pytest.mark.asyncio
    async def test_event_handler_called_on_store(self):
        mgr = HybridMemoryManager()
        mgr.register("a", TrackingBackend())
        events: list[MemoryEvent] = []
        mgr.on_event(events.append)
        await mgr.store("hello")
        assert len(events) == 1
        assert events[0].event_type == MemoryEventType.STORED
        assert events[0].backend == "a"
        assert "hello" in events[0].content

    @pytest.mark.asyncio
    async def test_event_handler_called_on_retrieve(self):
        mgr = HybridMemoryManager()
        b = TrackingBackend()
        mgr.register("a", b)
        await b.store("hello world")
        events: list[MemoryEvent] = []
        mgr.on_event(events.append)
        await mgr.retrieve("hello")
        assert len(events) >= 2
        queried_types = [e.event_type for e in events]
        assert MemoryEventType.QUERIED in queried_types

    @pytest.mark.asyncio
    async def test_event_handler_called_on_delete(self):
        mgr = HybridMemoryManager()
        b = TrackingBackend()
        mgr.register("a", b)
        await b.store("data")
        events: list[MemoryEvent] = []
        mgr.on_event(events.append)
        await mgr.delete("doc_1")
        assert len(events) == 1
        assert events[0].event_type == MemoryEventType.DELETED

    @pytest.mark.asyncio
    async def test_event_handler_exception_does_not_crash(self):
        mgr = HybridMemoryManager()
        mgr.register("a", TrackingBackend())

        def bad_handler(_event: MemoryEvent) -> None:
            raise RuntimeError("handler crash")

        mgr.on_event(bad_handler)
        await mgr.store("hello")

    @pytest.mark.asyncio
    async def test_event_timestamp_set(self):
        mgr = HybridMemoryManager()
        mgr.register("a", TrackingBackend())
        events: list[MemoryEvent] = []
        mgr.on_event(events.append)
        await mgr.store("hello")
        assert events[0].timestamp > 0

    def test_memory_event_dataclass(self):
        event = MemoryEvent(
            event_type=MemoryEventType.STORED,
            backend="test",
            content="hello",
            doc_id="d1",
        )
        assert event.event_type == "memory.stored"
        assert event.backend == "test"
        assert event.timestamp > 0

    def test_memory_event_factory_functions(self):
        from aios.memory.events import (
            memory_cleared,
            memory_deleted,
            memory_expired,
            memory_queried,
            memory_retrieved,
            memory_stored,
            memory_summarized,
        )

        e = memory_stored("b", "d1", "content")
        assert e.event_type == MemoryEventType.STORED

        e = memory_retrieved("b", "q", 3)
        assert e.event_type == MemoryEventType.RETRIEVED
        assert e.result_count == 3

        e = memory_deleted("b", "d1")
        assert e.event_type == MemoryEventType.DELETED

        e = memory_cleared("b")
        assert e.event_type == MemoryEventType.CLEARED

        e = memory_summarized("b", "d1", "summary")
        assert e.event_type == MemoryEventType.SUMMARIZED

        e = memory_expired("b", "d1")
        assert e.event_type == MemoryEventType.EXPIRED

        e = memory_queried("b", "q", 5)
        assert e.event_type == MemoryEventType.QUERIED
        assert e.result_count == 5


# ---------------------------------------------------------------------------
# Integration: manager + real backends
# ---------------------------------------------------------------------------

class TestManagerIntegration:
    """Integration tests using real memory backends together."""

    @pytest.mark.asyncio
    async def test_multi_backend_store_and_retrieve(self):
        mgr = HybridMemoryManager()
        st = ShortTermMemory()
        ep = EpisodicMemory()
        ent = EntityMemory()
        cache = CacheMemory()
        mgr.register("short_term", st)
        mgr.register("episodic", ep)
        mgr.register("entity", ent)
        mgr.register("cache", cache)

        await mgr.store("Alice visited the cardiologist", backend="entity")
        await mgr.store("Meeting with Dr. Smith at 3pm", backend="episodic")
        await mgr.store("Heart rate 72 bpm", backend="short_term")

        results = await mgr.retrieve("cardiologist", top_k=10)
        assert len(results) >= 1
        contents = [r.content for r in results]
        assert any("cardiologist" in c for c in contents)

    @pytest.mark.asyncio
    async def test_count_across_backends(self):
        mgr = HybridMemoryManager()
        mgr.register("st", ShortTermMemory())
        mgr.register("ep", EpisodicMemory())
        await mgr.store("one", backend="st")
        await mgr.store("two", backend="st")
        await mgr.store("three", backend="ep")
        counts = await mgr.count()
        assert counts == {"st": 2, "ep": 1}

    @pytest.mark.asyncio
    async def test_delete_across_backends(self):
        mgr = HybridMemoryManager()
        mgr.register("st", ShortTermMemory())
        mgr.register("ep", EpisodicMemory())
        id1 = await mgr.store("one", backend="st")
        await mgr.store("two", backend="ep")
        await mgr.delete(id1, backend="st")
        assert await mgr.count() == {"st": 0, "ep": 1}
