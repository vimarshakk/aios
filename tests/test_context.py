"""Tests for the Context Engine (Phase 2)."""

from unittest.mock import AsyncMock

import pytest

from aios.agents.types import Message, Role
from aios.context.builder import BuildResult, ContextBuilder, ContextSpec
from aios.context.inject import format_memory_for_injection, inject_context
from aios.context.ranking import RelevanceRanker, ScoredResult
from aios.context.retriever import MemoryHit, MemoryRetriever, RetrievalResult
from aios.context.summarizer import ContextSummarizer
from aios.context.window import ConversationWindow, estimate_message_tokens

# ── ConversationWindow ───────────────────────────────────────────────


class TestConversationWindow:
    def test_empty_messages(self):
        window = ConversationWindow(max_tokens=1000)
        assert window.fit([]) == []

    def test_single_message(self):
        window = ConversationWindow(max_tokens=1000)
        msgs = [Message(role=Role.USER, content="Hello")]
        result = window.fit(msgs)
        assert len(result) == 1
        assert result[0].content == "Hello"

    def test_system_message_always_kept(self):
        window = ConversationWindow(max_tokens=1000)
        msgs = [
            Message(role=Role.SYSTEM, content="You are helpful."),
            Message(role=Role.USER, content="Hi"),
            Message(role=Role.ASSISTANT, content="Hello!"),
        ]
        result = window.fit(msgs)
        assert result[0].role.value == "system"

    def test_last_user_message_always_kept(self):
        window = ConversationWindow(max_tokens=1000)
        msgs = [
            Message(role=Role.USER, content="First"),
            Message(role=Role.ASSISTANT, content="Reply 1"),
            Message(role=Role.USER, content="Second"),
            Message(role=Role.ASSISTANT, content="Reply 2"),
            Message(role=Role.USER, content="Last"),
        ]
        result = window.fit(msgs)
        assert result[-1].content == "Last"
        assert result[-1].role.value == "user"

    def test_fits_within_budget(self):
        window = ConversationWindow(max_tokens=50)
        msgs = [
            Message(role=Role.SYSTEM, content="sys"),
            Message(role=Role.USER, content="q"),
            Message(role=Role.ASSISTANT, content="a"),
            Message(role=Role.USER, content="q2"),
        ]
        result = window.fit(msgs)
        # Should include system + last user, possibly more
        total = sum(estimate_message_tokens(m) for m in result)
        assert total <= 50 + 10  # small tolerance

    def test_trim_to_fit(self):
        window = ConversationWindow(max_tokens=1000)
        msgs = [Message(role=Role.USER, content="Hello")]
        result = window.trim_to_fit(msgs, max_tokens=50)
        assert len(result) >= 1


# ── RelevanceRanker ──────────────────────────────────────────────────


class TestRelevanceRanker:
    def test_rank_empty(self):
        ranker = RelevanceRanker()
        assert ranker.rank("hello", []) == []

    def test_rank_exact_match(self):
        ranker = RelevanceRanker(min_score=0.0)
        candidates = [
            RetrievalResult(content="hello world", score=0.9, source="test"),
        ]
        result = ranker.rank("hello world", candidates)
        assert len(result) == 1
        assert result[0].score > 0.5

    def test_rank_partial_match(self):
        ranker = RelevanceRanker(min_score=0.0)
        candidates = [
            RetrievalResult(content="hello world", score=0.8, source="a"),
            RetrievalResult(content="goodbye moon", score=0.8, source="b"),
        ]
        result = ranker.rank("hello", candidates)
        # "hello world" should rank higher than "goodbye moon"
        assert result[0].content == "hello world"

    def test_filter_relevant(self):
        ranker = RelevanceRanker(min_score=0.0)
        candidates = [
            ScoredResult(content="a", score=0.9),
            ScoredResult(content="b", score=0.5),
            ScoredResult(content="c", score=0.1),
        ]
        result = ranker.filter_relevant(candidates, top_k=2)
        assert len(result) == 2
        assert result[0].score >= result[1].score

    def test_min_score_filter(self):
        ranker = RelevanceRanker(min_score=0.5)
        candidates = [
            RetrievalResult(content="exact match query", score=0.95, source="a"),
            RetrievalResult(content="unrelated content", score=0.1, source="b"),
        ]
        result = ranker.rank("query", candidates)
        assert all(r.score >= 0.5 for r in result)


# ── MemoryRetriever ──────────────────────────────────────────────────


class TestMemoryRetriever:
    @pytest.mark.asyncio
    async def test_empty_backends(self):
        retriever = MemoryRetriever()
        results = await retriever.retrieve("test query")
        assert results == []

    @pytest.mark.asyncio
    async def test_with_mock_backend(self):
        mock_backend = AsyncMock()
        mock_backend.search.return_value = [
            MemoryHit(text="result 1", score=0.9),
            MemoryHit(text="result 2", score=0.7),
        ]

        retriever = MemoryRetriever(backends=[mock_backend])
        results = await retriever.retrieve("query", top_k=5)

        assert len(results) == 2
        assert results[0].content == "result 1"
        assert results[0].score == 0.9
        assert results[0].source == "AsyncMock"

    @pytest.mark.asyncio
    async def test_multiple_backends(self):
        backend1 = AsyncMock()
        backend1.search.return_value = [
            MemoryHit(text="from backend 1", score=0.8),
        ]
        backend2 = AsyncMock()
        backend2.search.return_value = [
            MemoryHit(text="from backend 2", score=0.6),
        ]

        retriever = MemoryRetriever(backends=[backend1, backend2])
        results = await retriever.retrieve("query")

        assert len(results) == 2
        # Sorted by score descending
        assert results[0].score >= results[1].score

    @pytest.mark.asyncio
    async def test_backend_error_handled(self):
        mock_backend = AsyncMock()
        mock_backend.search.side_effect = RuntimeError("Connection failed")

        retriever = MemoryRetriever(backends=[mock_backend])
        results = await retriever.retrieve("query")
        assert results == []

    @pytest.mark.asyncio
    async def test_add_backend(self):
        retriever = MemoryRetriever()
        mock_backend = AsyncMock()
        mock_backend.search.return_value = [MemoryHit(text="ok", score=1.0)]

        retriever.add_backend(mock_backend)
        results = await retriever.retrieve("test")
        assert len(results) == 1


# ── ContextSummarizer ────────────────────────────────────────────────


class TestContextSummarizer:
    @pytest.mark.asyncio
    async def test_empty_messages(self):
        summarizer = ContextSummarizer()
        result = await summarizer.summarize([])
        assert result == ""

    @pytest.mark.asyncio
    async def test_truncation_summary(self):
        summarizer = ContextSummarizer()
        messages = [
            Message(role=Role.USER, content="What is AI?"),
            Message(role=Role.ASSISTANT, content="AI is artificial intelligence."),
            Message(role=Role.USER, content="How does it work?"),
        ]
        result = await summarizer.summarize(messages)
        assert "AI" in result or "artificial" in result

    @pytest.mark.asyncio
    async def test_llm_summarize(self):
        mock_llm = AsyncMock(return_value="AI is a field of computer science.")
        summarizer = ContextSummarizer(llm_fn=mock_llm)

        messages = [
            Message(role=Role.USER, content="Tell me about AI"),
            Message(role=Role.ASSISTANT, content="AI is artificial intelligence..."),
        ]
        result = await summarizer.summarize(messages)
        assert "AI" in result
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_fallback_on_error(self):
        mock_llm = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        summarizer = ContextSummarizer(llm_fn=mock_llm)

        messages = [
            Message(role=Role.USER, content="Hello"),
            Message(role=Role.ASSISTANT, content="Hi"),
        ]
        result = await summarizer.summarize(messages)
        # Should fall back to truncation
        assert "Hello" in result or "Hi" in result

    def test_split_for_summary_short(self):
        summarizer = ContextSummarizer()
        msgs = [Message(role=Role.USER, content="hi")]
        to_summarize, to_keep = summarizer.split_for_summary(msgs, keep_recent=10)
        assert to_summarize == []
        assert len(to_keep) == 1

    def test_split_for_summary_long(self):
        summarizer = ContextSummarizer()
        msgs = [Message(role=Role.SYSTEM, content="sys")]
        msgs += [Message(role=Role.USER, content=f"msg-{i}") for i in range(20)]
        to_summarize, to_keep = summarizer.split_for_summary(msgs, keep_recent=5)
        assert len(to_summarize) > 0
        # System messages should be in to_keep
        assert any(m.role.value == "system" for m in to_keep)


# ── inject_context ───────────────────────────────────────────────────


class TestInjectContext:
    def test_no_context(self):
        msgs = [Message(role=Role.USER, content="Hello")]
        result = inject_context(msgs)
        assert result == msgs

    def test_inject_text(self):
        msgs = [Message(role=Role.USER, content="Hello")]
        result = inject_context(msgs, context_text="Some context")
        assert len(result) == 2
        assert "[Context]" in result[0].content
        assert result[1].content == "Hello"

    def test_inject_after_system(self):
        msgs = [
            Message(role=Role.SYSTEM, content="You are helpful."),
            Message(role=Role.USER, content="Hello"),
        ]
        result = inject_context(msgs, context_text="extra info")
        assert len(result) == 3
        assert result[0].role.value == "system"
        assert result[1].role.value == "system"
        assert "[Context]" in result[1].content
        assert result[2].content == "Hello"

    def test_inject_memory_items(self):
        msgs = [Message(role=Role.USER, content="Hi")]
        result = inject_context(msgs, memory_items=["fact 1", "fact 2"])
        assert "fact 1" in result[0].content
        assert "fact 2" in result[0].content

    def test_format_memory_for_injection(self):
        results = [
            {"content": "hello", "source": "test", "score": 0.9},
            {"content": "world"},
        ]
        text = format_memory_for_injection(results)
        assert "[test] hello" in text
        assert "world" in text

    def test_format_memory_empty(self):
        assert format_memory_for_injection([]) == ""


# ── ContextBuilder ───────────────────────────────────────────────────


class TestContextBuilder:
    @pytest.mark.asyncio
    async def test_simple_build(self):
        builder = ContextBuilder()
        spec = ContextSpec(
            query="What is AI?",
            system_prompt="You are helpful.",
        )
        result = await builder.build(spec)
        assert isinstance(result, BuildResult)
        assert len(result.messages) >= 2
        # System prompt + user query
        assert result.messages[0].role.value == "system"
        assert result.messages[-1].role.value == "user"
        assert result.messages[-1].content == "What is AI?"

    @pytest.mark.asyncio
    async def test_build_with_memory(self):
        mock_backend = AsyncMock()
        mock_backend.search.return_value = [
            MemoryHit(text="AI is artificial intelligence", score=0.95),
        ]

        retriever = MemoryRetriever(backends=[mock_backend])
        builder = ContextBuilder(retriever=retriever)

        spec = ContextSpec(query="What is AI?", memory_top_k=3)
        result = await builder.build(spec)

        assert len(result.memory_used) == 1
        assert result.memory_used[0].content == "AI is artificial intelligence"

    @pytest.mark.asyncio
    async def test_build_with_conversation(self):
        builder = ContextBuilder()
        conversation = [
            Message(role=Role.USER, content="Hello"),
            Message(role=Role.ASSISTANT, content="Hi there!"),
        ]
        spec = ContextSpec(
            query="How are you?",
            conversation=conversation,
        )
        result = await builder.build(spec)

        # Should have conversation + user query
        assert result.final_message_count >= 3
        assert result.messages[-1].content == "How are you?"

    @pytest.mark.asyncio
    async def test_build_simple(self):
        builder = ContextBuilder()
        messages = await builder.build_simple(
            "Hello",
            system_prompt="Be helpful.",
        )
        assert len(messages) >= 2
        assert messages[0].role.value == "system"
        assert messages[-1].content == "Hello"

    @pytest.mark.asyncio
    async def test_build_result_metadata(self):
        builder = ContextBuilder()
        spec = ContextSpec(query="test", system_prompt="sys")
        result = await builder.build(spec)
        assert result.original_message_count == 0
        assert result.final_message_count >= 2
        assert result.was_summarized is False
        assert result.memory_used == []


# ── Token estimation ─────────────────────────────────────────────────


class TestTokenEstimation:
    def test_estimate_tokens(self):
        msg = Message(role=Role.USER, content="Hello, world!")
        tokens = estimate_message_tokens(msg)
        assert tokens > 0
        assert tokens < 50

    def test_long_message(self):
        msg = Message(role=Role.USER, content="x" * 1000)
        tokens = estimate_message_tokens(msg)
        assert tokens > 200
