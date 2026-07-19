"""ConversationWindow — sliding window management for message lists."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aios.agents.types import Message


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return max(1, len(text) // 4)


def estimate_message_tokens(msg: Message) -> int:
    """Estimate token count for a single message."""
    content_tokens = _estimate_tokens(msg.content)
    # Role token + formatting overhead
    return content_tokens + 4


class ConversationWindow:
    """Manage a sliding window of conversation messages within a token budget.

    Keeps the system prompt (if present) and the most recent messages
    that fit within the token limit.
    """

    def __init__(self, max_tokens: int = 8000) -> None:
        self._max_tokens = max_tokens

    def fit(self, messages: list[Message]) -> list[Message]:
        """Return messages that fit within the token budget.

        Strategy:
        1. Always keep the system message (first SYSTEM message)
        2. Always keep the last user message
        3. Fill remaining budget with most recent messages (working backwards)
        4. Drop oldest messages that don't fit
        """
        if not messages:
            return []

        budget = self._max_tokens
        system_msg: Message | None = None

        # Separate system message if present
        if messages[0].role.value == "system":
            system_msg = messages[0]
            budget -= estimate_message_tokens(system_msg)

        non_system = [m for m in messages if m.role.value != "system"]

        if not non_system:
            return [system_msg] if system_msg else []

        # Always include the last user message
        last_msg = non_system[-1]
        budget -= estimate_message_tokens(last_msg)

        # Fill backwards from second-to-last
        included: list[Message] = [last_msg]
        for msg in reversed(non_system[:-1]):
            msg_tokens = estimate_message_tokens(msg)
            if budget - msg_tokens >= 0:
                included.append(msg)
                budget -= msg_tokens
            else:
                break

        included.reverse()

        if system_msg:
            return [system_msg, *included]
        return included

    def trim_to_fit(self, messages: list[Message], max_tokens: int | None = None) -> list[Message]:
        """Trim messages to fit within a token budget (uses instance default if not specified)."""
        old_max = self._max_tokens
        if max_tokens is not None:
            self._max_tokens = max_tokens
        result = self.fit(messages)
        self._max_tokens = old_max
        return result
