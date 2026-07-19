"""ContextBuilder — assembles complete context for every agent invocation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from aios.agents.types import Message, Role
from aios.context.inject import format_memory_for_injection
from aios.context.ranking import RelevanceRanker
from aios.context.retriever import MemoryRetriever, RetrievalResult
from aios.context.summarizer import ContextSummarizer, LLMFn
from aios.context.window import ConversationWindow

if TYPE_CHECKING:
    from aios.memory.manager import HybridMemoryManager


@dataclass
class ContextSpec:
    """Specification for building context for an agent invocation."""

    query: str
    system_prompt: str = ""
    conversation: list[Message] = field(default_factory=list)
    max_context_tokens: int = 8000
    memory_top_k: int = 5
    memory_min_score: float = 0.5
    keep_recent_messages: int = 10


@dataclass
class BuildResult:
    """Result of context building."""

    messages: list[Message] = field(default_factory=list)
    memory_used: list[RetrievalResult] = field(default_factory=list)
    was_summarized: bool = False
    original_message_count: int = 0
    final_message_count: int = 0


class ContextBuilder:
    """Build complete context for an agent invocation.

    Assembles system prompt + retrieved memory + conversation history
    into a message list ready for LLM consumption.

    Pipeline:
    1. Start with system prompt
    2. Retrieve relevant memory (semantic search)
    3. Rank retrieved items by relevance
    4. Summarize old conversation if too long
    5. Apply sliding window to fit token budget
    6. Inject context into message list
    7. Add user query
    """

    def __init__(
        self,
        retriever: MemoryRetriever | None = None,
        memory_manager: HybridMemoryManager | None = None,
        summarizer: ContextSummarizer | None = None,
        ranker: RelevanceRanker | None = None,
        window: ConversationWindow | None = None,
        llm_fn: LLMFn | None = None,
    ) -> None:
        self._memory_manager = memory_manager
        self._retriever = retriever or MemoryRetriever()
        self._summarizer = summarizer or ContextSummarizer(llm_fn=llm_fn)
        self._ranker = ranker or RelevanceRanker()
        self._window = window or ConversationWindow()

    async def build(self, spec: ContextSpec) -> BuildResult:
        """Build context messages from the given specification.

        Returns a BuildResult with the assembled messages and metadata.
        """
        messages: list[Message] = []
        memory_used: list[RetrievalResult] = []
        was_summarized = False

        # 1. System prompt
        if spec.system_prompt:
            messages.append(Message(role=Role.SYSTEM, content=spec.system_prompt))

        # 2. Retrieve relevant memory
        if spec.query:
            if self._memory_manager:
                raw_results = await self._memory_manager.retrieve(
                    spec.query,
                    top_k=spec.memory_top_k,
                    min_score=spec.memory_min_score,
                )
            else:
                raw_results = await self._retriever.retrieve(
                    spec.query,
                    top_k=spec.memory_top_k,
                    min_score=spec.memory_min_score,
                )

            # 3. Rank by relevance
            if raw_results:
                scored = self._ranker.rank(spec.query, raw_results)
                memory_used = [
                    RetrievalResult(
                        content=s.content,
                        score=s.score,
                        metadata=s.metadata,
                        source=s.source,
                    )
                    for s in scored
                ]

        # 4. Inject memory context
        if memory_used:
            memory_text = format_memory_for_injection([
                {"content": m.content, "source": m.source, "score": m.score}
                for m in memory_used
            ])
            if memory_text:
                messages.append(Message(
                    role=Role.SYSTEM,
                    content=f"[Memory Context]\n{memory_text}\n[/Memory Context]",
                ))

        # 5. Summarize old conversation if needed
        conversation = list(spec.conversation)
        original_count = len(conversation)

        if conversation:
            to_summarize, to_keep = self._summarizer.split_for_summary(
                conversation,
                keep_recent=spec.keep_recent_messages,
            )
            if to_summarize:
                summary = await self._summarizer.summarize(to_summarize)
                if summary:
                    messages.append(Message(
                        role=Role.SYSTEM,
                        content=f"[Conversation Summary]\n{summary}\n[/Conversation Summary]",
                    ))
                    was_summarized = True
                conversation = to_keep

        # 6. Apply sliding window
        messages.extend(conversation)
        messages = self._window.fit(messages)

        # 7. Add user query
        if spec.query:
            messages.append(Message(role=Role.USER, content=spec.query))

        return BuildResult(
            messages=messages,
            memory_used=memory_used,
            was_summarized=was_summarized,
            original_message_count=original_count,
            final_message_count=len(messages),
        )

    async def build_simple(
        self,
        query: str,
        *,
        system_prompt: str = "",
        conversation: list[Message] | None = None,
        max_context_tokens: int = 8000,
    ) -> list[Message]:
        """Simplified interface that returns just the message list."""
        spec = ContextSpec(
            query=query,
            system_prompt=system_prompt,
            conversation=conversation or [],
            max_context_tokens=max_context_tokens,
        )
        result = await self.build(spec)
        return result.messages
