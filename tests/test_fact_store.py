"""Tests for JSONLFactStore."""

import tempfile
from pathlib import Path

import pytest

from aios.memory.fact_store import Fact, JSONLFactStore


class TestJSONLFactStore:
    def _make_store(self):
        tmpdir = tempfile.mkdtemp()
        return JSONLFactStore(path=str(Path(tmpdir) / "facts.jsonl"))

    @pytest.mark.asyncio
    async def test_store_and_list_all(self):
        store = self._make_store()
        fact = Fact(id="f1", subject="Paris", predicate="capital_of", obj="France")
        await store.store(fact)
        all_facts = await store.list_all()
        assert len(all_facts) == 1
        assert all_facts[0].subject == "Paris"

    @pytest.mark.asyncio
    async def test_store_multiple(self):
        store = self._make_store()
        await store.store(Fact(id="f1", subject="A", predicate="rel", obj="B"))
        await store.store(Fact(id="f2", subject="C", predicate="rel", obj="D"))
        await store.store(Fact(id="f3", subject="E", predicate="rel", obj="F"))
        all_facts = await store.list_all()
        assert len(all_facts) == 3

    @pytest.mark.asyncio
    async def test_delete(self):
        store = self._make_store()
        await store.store(Fact(id="f1", subject="X", predicate="rel", obj="Y"))
        assert await store.delete("f1") is True
        all_facts = await store.list_all()
        assert len(all_facts) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        store = self._make_store()
        assert await store.delete("nonexistent") is False

    @pytest.mark.asyncio
    async def test_query_by_subject(self):
        store = self._make_store()
        await store.store(Fact(id="f1", subject="Paris", predicate="capital_of", obj="France"))
        await store.store(Fact(id="f2", subject="Berlin", predicate="capital_of", obj="Germany"))
        results = await store.query(subject="Paris")
        assert len(results) == 1
        assert results[0].obj == "France"

    @pytest.mark.asyncio
    async def test_query_by_predicate(self):
        store = self._make_store()
        await store.store(Fact(id="f1", subject="A", predicate="is_a", obj="B"))
        await store.store(Fact(id="f2", subject="C", predicate="rel", obj="D"))
        results = await store.query(predicate="is_a")
        assert len(results) == 1
        assert results[0].subject == "A"

    @pytest.mark.asyncio
    async def test_empty_store(self):
        store = self._make_store()
        assert len(await store.list_all()) == 0
        assert await store.query(subject="anything") == []
