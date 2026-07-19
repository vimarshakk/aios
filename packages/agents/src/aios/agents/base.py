"""Abstract base classes for AIOS agents.

Extracted from OpenJarvis agents/_stubs.py (Apache 2.0).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aios.agents.types import Message, Trace


class BaseAgent(ABC):
    """All agents must implement this interface."""

    name: str = "base"

    @abstractmethod
    async def run(self, query: str, *, trace: Trace | None = None) -> str:
        """Execute the agent on a query and return the final response."""
        ...

    @abstractmethod
    async def step(self, messages: list[Message], *, trace: Trace | None = None) -> Message:
        """Execute a single agent step (one LLM call + optional tool use)."""
        ...

    def describe(self) -> dict[str, Any]:
        """Return a JSON-serializable description of this agent."""
        return {"name": self.name, "type": type(self).__name__}


__all__ = ["BaseAgent"]
