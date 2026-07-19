"""Tests for the Unified Memory backends (Phase 3)."""

import time

import pytest

from aios.memory.backend import MemoryBackend
from aios.memory.cache import CacheMemory
from aios.memory.entity import EntityMemory
from aios.memory.episodic import EpisodicMemory
from aios.memory.short_term import ShortTermMemory


class TestShortTermMemory:
    """Tests for ShortTermMemory (sliding window)."""

    @pytest.mark.asyncio
    async def test_store_and_count(self):
        mem = ShortTermMemory()
        assert await mem.count() == 0
        await mem.store("hello")
        assert await mem.count() == 1
        await mem.store("world")
        assert await mem.count() == 2

    @pytest.mark.asyncio
    async def test_retrieve_exact_match(self):
        mem = ShortTermMemory()
        await mem.store("the quick brown fox")
        results = await mem.retrieve("fox")
        assert len(results) == 1
        assert "fox" in results[0].content
        assert results[0].score > 0.5

    @pytest.mark.asyncio
    async def test_retrieve_word_overlap(self):
        mem = ShortTermMemory()
        await mem.store("machine learning algorithms")
        results = await mem.retrieve("machine learning")
        assert len(results) == 1
        assert results[0].score > 0.3

    @pytest.mark.asyncio
    async def test_retrieve_no_match(self):
        mem = ShortTermMemory()
        await mem.store("hello")
        results = await mem.retrieve("xyz", min_score=0.1)
        assert results == []

    @pytest.mark.asyncio
    async def test_eviction(self):
        mem = ShortTermMemory(max_entries=3)
        await mem.store("first")
        await mem.store("second")
        await mem.store("third")
        assert await mem.count() == 3
        await mem.store("fourth")
        assert await mem.count() == 3

    @pytest.mark.asyncio
    async def test_delete(self):
        mem = ShortTermMemory()
        doc_id = await mem.store("delete me")
        assert await mem.has(doc_id)
        assert await mem.delete(doc_id)
        assert not await mem.has(doc_id)

    @pytest.mark.asyncio
    async def test_clear(self):
        mem = ShortTermMemory()
        await mem.store("one")
        await mem.store("two")
        await mem.clear()
        assert await mem.count() == 0

    @pytest.mark.asyncio
    async def test_has(self):
        mem = ShortTermMemory()
        doc_id = await mem.store("exists")
        assert await mem.has(doc_id)
        assert not await mem.has("nonexistent")

    @pytest.mark.asyncio
    async def test_min_score_filter(self):
        mem = ShortTermMemory()
        await mem.store("hello world")
        results = await mem.retrieve("completely unrelated", min_score=0.5)
        assert results == []

    @pytest.mark.asyncio
    async def test_top_k(self):
        mem = ShortTermMemory()
        for i in range(10):
            await mem.store(f"item {i} about cats")
        results = await mem.retrieve("cats", top_k=3)
        assert len(results) == 3

    def test_get_recent(self):
        import asyncio

        mem = ShortTermMemory()

        async def _run():
            await mem.store("first")
            await mem.store("second")
            return mem.get_recent(1)

        recent = asyncio.run(_run())
        assert len(recent) == 1
        assert recent[0]["content"] == "second"


class TestEpisodicMemory:
    """Tests for EpisodicMemory (timestamped entries)."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        mem = EpisodicMemory()
        doc_id = await mem.store(
            "Patient visit",
            metadata={"tags": ["checkup"]},
        )
        assert doc_id
        results = await mem.retrieve("visit")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_retrieve_by_tag(self):
        mem = EpisodicMemory()
        await mem.store("checkup result", metadata={"tags": ["checkup"]})
        await mem.store("surgery note", metadata={"tags": ["surgery"]})
        results = await mem.retrieve("result", min_score=0.0)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_session_filtering(self):
        mem = EpisodicMemory()
        await mem.store("session 1 note", metadata={"session_id": "s1"})
        await mem.store("session 2 note", metadata={"session_id": "s2"})
        episodes = mem.get_by_session("s1")
        assert len(episodes) == 1
        assert "session 1" in episodes[0].content

    @pytest.mark.asyncio
    async def test_time_range(self):
        mem = EpisodicMemory()
        now = time.time()
        await mem.store("recent event", metadata={"timestamp": now})
        results = mem.get_by_time_range(now - 1, now + 1)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_delete(self):
        mem = EpisodicMemory()
        doc_id = await mem.store("delete me")
        assert await mem.delete(doc_id)


class TestEntityMemory:
    """Tests for EntityMemory (entity-relationship store)."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        mem = EntityMemory()
        await mem.store(
            "Alice is a cardiologist",
            metadata={"entity_name": "Alice", "entity_type": "person"},
        )
        results = await mem.retrieve("Alice")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_by_name(self):
        mem = EntityMemory()
        await mem.store(
            "Bob is a patient",
            metadata={"entity_name": "Bob", "entity_type": "patient"},
        )
        entity = mem.get_entity_by_name("Bob")
        assert entity is not None
        assert entity.name == "Bob"

    @pytest.mark.asyncio
    async def test_update_existing(self):
        mem = EntityMemory()
        await mem.store(
            "Alice",
            metadata={"entity_name": "Alice", "entity_type": "person"},
        )
        await mem.store(
            "Alice",
            metadata={
                "entity_name": "Alice",
                "entity_type": "person",
                "age": 30,
            },
        )
        assert await mem.count() == 1

    @pytest.mark.asyncio
    async def test_add_relationship(self):
        mem = EntityMemory()
        alice_id = await mem.store(
            "Alice",
            metadata={"entity_name": "Alice", "entity_type": "doctor"},
        )
        await mem.store(
            "Bob",
            metadata={"entity_name": "Bob", "entity_type": "patient"},
        )
        result = mem.add_relationship(alice_id, "treats", "Bob")
        assert result is True
        entity = mem.get_entity_by_name("Alice")
        assert entity is not None
        assert len(entity.relationships) == 1
        assert entity.relationships[0]["target"] == "Bob"

    @pytest.mark.asyncio
    async def test_get_by_type(self):
        mem = EntityMemory()
        await mem.store(
            "Alice",
            metadata={"entity_name": "Alice", "entity_type": "doctor"},
        )
        await mem.store(
            "Bob",
            metadata={"entity_name": "Bob", "entity_type": "patient"},
        )
        doctors = mem.get_entities_by_type("doctor")
        assert len(doctors) == 1
        assert doctors[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_delete(self):
        mem = EntityMemory()
        doc_id = await mem.store(
            "Delete me",
            metadata={"entity_name": "Delete", "entity_type": "temp"},
        )
        assert await mem.delete(doc_id)


class TestCacheMemory:
    """Tests for CacheMemory (LRU with TTL)."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        mem = CacheMemory()
        await mem.store("cached data")
        results = await mem.retrieve("cached")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        mem = CacheMemory()
        await mem.store("cached item")
        # First call — cache miss
        await mem.retrieve("cached")
        # Second call — cache hit
        results = await mem.retrieve("cached")
        assert len(results) == 1
        # LRU cache should have the results

    @pytest.mark.asyncio
    async def test_invalidate(self):
        mem = CacheMemory()
        await mem.store("invalidate me")
        # Populate cache
        await mem.retrieve("invalidate")
        count = mem.invalidate("invalidate")
        assert count >= 1

    @pytest.mark.asyncio
    async def test_invalidate_all(self):
        mem = CacheMemory()
        await mem.store("one")
        await mem.store("two")
        await mem.retrieve("one")
        await mem.retrieve("two")
        count = mem.invalidate()
        assert count == 2


class TestMemoryBackendConformance:
    """Conformance checks — all backends must satisfy the MemoryBackend ABC contract."""

    @pytest.mark.parametrize(
        "backend",
        [ShortTermMemory(), EpisodicMemory(), EntityMemory(), CacheMemory()],
    )
    @pytest.mark.asyncio
    async def test_round_trip(self, backend: MemoryBackend):
        doc_id = await backend.store("test content")
        assert doc_id
        results = await backend.retrieve("test")
        assert len(results) >= 1
        assert any("test" in r.content for r in results)
        deleted = await backend.delete(doc_id)
        assert deleted

    @pytest.mark.parametrize(
        "backend",
        [ShortTermMemory(), EpisodicMemory(), EntityMemory(), CacheMemory()],
    )
    @pytest.mark.asyncio
    async def test_clear(self, backend: MemoryBackend):
        await backend.store("one")
        await backend.store("two")
        await backend.clear()
        assert await backend.count() == 0
