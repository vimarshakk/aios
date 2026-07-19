"""Memory Agent — store, retrieve, and reason over memories."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aios.agents.base import BaseAgent
from aios.agents.types import Message, Role, Trace
from aios.tools.builtin import MemoryTool

if TYPE_CHECKING:
    from aios.agents.engine import InferenceEngine

_MEMORY_SYSTEM = """\
You are AIOS Memory Agent — a personal knowledge manager.

You help users store important information, retrieve past memories,
and reason over their knowledge base.

You can:
- Store facts, notes, and information with meaningful keys
- Retrieve specific memories by key
- Search across all memories
- Summarize what you know about a topic
- Forget/delete outdated information

Always use descriptive, meaningful keys. Organize memories logically.
"""


class MemoryAgent(BaseAgent):
    """Agent specialized in memory management."""

    name = "memory"

    def __init__(self, engine: InferenceEngine, model: str = "ollama/llama3.2") -> None:
        self._engine = engine
        self._model = model
        self._memory = MemoryTool()

    async def run(self, query: str, *, trace: Trace | None = None) -> str:
        q_lower = query.lower()

        # Auto-detect intent
        if any(w in q_lower for w in ("remember", "store", "save", "note", "keep")):
            # Extract key-value from query with LLM
            extract_msg = [
                Message(
                    role=Role.SYSTEM,
                    content=(
                        "Extract a key and value to store in memory. "
                        "Reply with exactly: KEY: <key>\nVALUE: <value>"
                    ),
                ),
                Message(role=Role.USER, content=query),
            ]
            result = await self._engine.complete(extract_msg, model=self._model, max_tokens=200)
            text = result.content
            key_match = __import__("re").search(r"KEY:\s*(.+)", text)
            val_match = __import__("re").search(r"VALUE:\s*(.+)", text, __import__("re").DOTALL)
            if key_match and val_match:
                key = key_match.group(1).strip()
                value = val_match.group(1).strip()
                await self._memory.execute(action="store", key=key, value=value)
                return f"✅ Stored memory: **{key}**\n> {value}"

        if any(w in q_lower for w in ("recall", "retrieve", "what do you know", "remember")):
            list_result = await self._memory.execute(action="list")
            if not list_result.success or "empty" in list_result.content:
                return "Memory is empty. Tell me something to remember!"
            messages = [
                Message(role=Role.SYSTEM, content=_MEMORY_SYSTEM),
                Message(
                    role=Role.USER,
                    content=(
                        f"Query: {query}\n\nAvailable memories:\n"
                        f"{list_result.content}\n\n"
                        "Answer based on these memories."
                    ),
                ),
            ]
            result = await self._engine.complete(messages, model=self._model, max_tokens=1024)
            return result.content

        if any(w in q_lower for w in ("forget", "delete", "remove")):
            messages = [
                Message(
                    role=Role.SYSTEM,
                    content="Extract the memory key to delete. Reply with just the key.",
                ),
                Message(role=Role.USER, content=query),
            ]
            result = await self._engine.complete(messages, model=self._model, max_tokens=50)
            key = result.content.strip()
            await self._memory.execute(action="delete", key=key)
            return f"🗑️ Deleted memory: **{key}**"

        # General memory query — search + answer
        search_result = await self._memory.execute(action="search", query=query)
        context = search_result.content if search_result.success else "No relevant memories found."
        messages = [
            Message(role=Role.SYSTEM, content=_MEMORY_SYSTEM),
            Message(role=Role.USER, content=f"Query: {query}\n\nRelevant memories:\n{context}"),
        ]
        result = await self._engine.complete(messages, model=self._model, max_tokens=1024)
        return result.content

    async def step(self, messages: list[Message], *, trace: Trace | None = None) -> Message:
        result = await self._engine.complete(messages, model=self._model)
        return Message(role=Role.ASSISTANT, content=result.content)

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "MemoryAgent",
            "capabilities": ["store_memory", "retrieve_memory", "search_memory"],
            "model": self._model,
            "description": (
                "Manages your personal knowledge base. Store facts, recall memories, search notes."
            ),
        }


__all__ = ["MemoryAgent"]
