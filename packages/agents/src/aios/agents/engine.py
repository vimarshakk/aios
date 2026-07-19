"""Abstract base classes for inference engines.

Extracted from OpenJarvis engine/_stubs.py (Apache 2.0).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from aios.agents.types import Message, ToolCall


@dataclass(slots=True)
class Usage:
    """Token usage from a completion."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(slots=True)
class CompletionResult:
    """Rich result from a non-streaming LLM completion."""

    content: str = ""
    usage: Usage = field(default_factory=Usage)
    model: str = ""
    finish_reason: str = "stop"
    tool_calls: list[ToolCall] = field(default_factory=list)
    latency_ms: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StreamChunk:
    """A single chunk from a streaming LLM response."""

    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    finish_reason: str | None = None
    usage: Usage | None = None
    done: bool = False


class EngineError(Exception):
    """Base error for inference engine failures."""


class EngineConnectionError(EngineError):
    """Failed to connect to the inference backend."""


class EngineContextLengthError(EngineError):
    """Prompt exceeds the model's context window."""


class InferenceEngine(ABC):
    """Abstract interface for LLM inference backends (Ollama, vLLM, OpenAI, etc.)."""

    name: str = "base"

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        *,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> CompletionResult:
        """Generate a completion from messages. Returns a rich CompletionResult."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        *,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a completion token by token."""
        ...
        yield  # make it a generator

    @abstractmethod
    async def health(self) -> bool:
        """Check if the engine backend is reachable and ready."""
        ...

    @abstractmethod
    def models(self) -> list[str]:
        """List available model identifiers on this engine."""
        ...

    async def close(self) -> None:  # noqa: B027
        """Release resources (HTTP clients, connections, threads)."""
        # Subclasses override to clean up. Default is no-op.

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "type": type(self).__name__}


__all__ = [
    "CompletionResult",
    "EngineConnectionError",
    "EngineContextLengthError",
    "EngineError",
    "InferenceEngine",
    "StreamChunk",
    "Usage",
]
