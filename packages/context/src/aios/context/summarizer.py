"""ContextSummarizer — compress long conversations to save context space."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aios.agents.types import Message

# Type alias for an async LLM completion function
LLMFn = Callable[[str], Awaitable[str]]


class ContextSummarizer:
    """Summarize old conversation turns to fit within context limits.

    Uses a pluggable LLM function to generate summaries. If no LLM is
    provided, falls back to a simple truncation-based approach.
    """

    def __init__(self, llm_fn: LLMFn | None = None) -> None:
        self._llm_fn = llm_fn

    async def summarize(self, messages: list[Message], *, max_summary_tokens: int = 500) -> str:
        """Summarize a list of messages into a concise string.

        If an LLM function is available, uses it for intelligent summarization.
        Otherwise falls back to extracting key points from messages.
        """
        if not messages:
            return ""

        if self._llm_fn:
            return await self._llm_summarize(messages, max_summary_tokens)
        return self._truncation_summary(messages)

    async def _llm_summarize(self, messages: list[Message], max_tokens: int) -> str:
        """Use LLM to generate a summary of the conversation."""
        conversation_text = "\n".join(
            f"{msg.role.value}: {msg.content}" for msg in messages
        )

        prompt = (
            "Summarize the following conversation concisely, preserving key facts, "
            "decisions, and context. Keep it under "
            f"~{max_tokens // 4} words.\n\n"
            f"Conversation:\n{conversation_text}\n\n"
            "Summary:"
        )

        try:
            return await self._llm_fn(prompt)  # type: ignore[misc]
        except Exception:
            return self._truncation_summary(messages)

    def _truncation_summary(self, messages: list[Message]) -> str:
        """Fallback: extract key messages as a summary."""
        if len(messages) <= 2:
            return "\n".join(f"{m.role.value}: {m.content}" for m in messages)

        # Take first, middle, and last messages
        key_indices = [0, len(messages) // 2, -1]
        parts = []
        for i in key_indices:
            msg = messages[i]
            parts.append(f"[{msg.role.value}]: {msg.content[:200]}")

        return "Previous conversation context:\n" + "\n".join(parts)

    def split_for_summary(
        self,
        messages: list[Message],
        keep_recent: int = 10,
    ) -> tuple[list[Message], list[Message]]:
        """Split messages into (to_summarize, to_keep).

        Returns the older messages that should be summarized, and the recent
        messages to keep as-is.
        """
        if len(messages) <= keep_recent:
            return [], messages

        # Keep system messages + recent non-system messages
        system_msgs = [m for m in messages if m.role.value == "system"]
        non_system = [m for m in messages if m.role.value != "system"]

        if len(non_system) <= keep_recent:
            return [], messages

        to_summarize = non_system[: len(non_system) - keep_recent]
        to_keep = non_system[len(non_system) - keep_recent :]

        return to_summarize, system_msgs + to_keep
