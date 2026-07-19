"""inject_context — prepend retrieved context to message list."""

from __future__ import annotations

from aios.agents.types import Message, Role


def inject_context(
    messages: list[Message],
    *,
    context_text: str = "",
    memory_items: list[str] | None = None,
) -> list[Message]:
    """Prepend context information to the message list.

    Injects context as a synthetic system message before the existing
    conversation, giving the LLM background knowledge.

    Args:
        messages: The existing conversation messages.
        context_text: Plain text context to inject (e.g., summary, retrieved docs).
        memory_items: List of memory snippets to include.

    Returns:
        New message list with context injected after any existing system message.
    """
    if not context_text and not memory_items:
        return messages

    parts: list[str] = []
    if context_text:
        parts.append(context_text)
    if memory_items:
        parts.append("Relevant memories:\n" + "\n".join(f"- {item}" for item in memory_items))

    injected_content = "\n\n".join(parts)

    # Find insertion point: after system messages, before user messages
    insert_idx = 0
    for i, msg in enumerate(messages):
        if msg.role.value == "system":
            insert_idx = i + 1
        else:
            break

    context_msg = Message(
        role=Role.SYSTEM,
        content=f"[Context]\n{injected_content}\n[/Context]",
    )

    return [*messages[:insert_idx], context_msg, *messages[insert_idx:]]


def format_memory_for_injection(results: list[dict]) -> str:
    """Format retrieval results into a context string.

    Each dict should have 'content' and optionally 'source', 'score'.
    """
    if not results:
        return ""

    parts = []
    for r in results:
        source = r.get("source", "")
        content = r.get("content", "")
        prefix = f"[{source}] " if source else ""
        parts.append(f"{prefix}{content}")

    return "\n".join(parts)
