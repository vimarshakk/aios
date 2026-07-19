"""OpenAI inference engine adapter.

Uses the official openai SDK. Supports OPENAI_API_KEY and
OPENAI_BASE_URL for OpenAI-compatible endpoints (vLLM, SGLang, etc.).
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any

from aios.agents.engine import (
    CompletionResult,
    EngineConnectionError,
    InferenceEngine,
    StreamChunk,
    Usage,
)
from aios.agents.registry import EngineRegistry
from aios.agents.types import Message, ToolCall

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@EngineRegistry.register("openai")
class OpenAIEngine(InferenceEngine):
    """OpenAI-compatible inference backend (also works with vLLM, SGLang, etc.)."""

    name = "openai"

    def __init__(self, *, api_key: str | None = None, base_url: str | None = None) -> None:
        try:
            import openai
        except ImportError as e:
            raise EngineConnectionError("openai package not installed") from e

        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self._client = openai.AsyncOpenAI(
            api_key=self._api_key or "dummy",
            base_url=self._base_url,
        )
        self._cached_models: list[str] = []

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
        t0 = time.monotonic()

        openai_messages = self._convert_messages(messages)

        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stop:
            request_kwargs["stop"] = stop

        # Pass tools if provided
        if "tools" in kwargs:
            request_kwargs["tools"] = kwargs["tools"]

        try:
            response = await self._client.chat.completions.create(**request_kwargs)
        except Exception as e:
            raise EngineConnectionError(f"OpenAI API error: {e}") from e

        choice = response.choices[0]
        message = choice.message
        content = message.content or ""

        tool_calls = []
        if message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id or f"openai_{i}",
                    name=tc.function.name,
                    arguments=tc.function.arguments or "{}",
                )
                for i, tc in enumerate(message.tool_calls)
            ]

        usage = Usage(
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
        )

        latency_ms = (time.monotonic() - t0) * 1000

        return CompletionResult(
            content=content,
            usage=usage,
            model=response.model,
            finish_reason=choice.finish_reason or "stop",
            tool_calls=tool_calls,
            latency_ms=latency_ms,
            raw={"id": response.id},
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop: list[str] | None = None,
        **_kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        openai_messages = self._convert_messages(messages)

        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if stop:
            request_kwargs["stop"] = stop

        try:
            response = await self._client.chat.completions.create(**request_kwargs)
            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield StreamChunk(content=delta.content)
                if chunk.choices and chunk.choices[0].finish_reason:
                    yield StreamChunk(finish_reason=chunk.choices[0].finish_reason, done=True)
        except Exception as e:
            raise EngineConnectionError(f"OpenAI streaming error: {e}") from e

    async def health(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False

    def models(self) -> list[str]:
        return self._cached_models

    async def list_models_async(self) -> list[str]:
        try:
            response = await self._client.models.list()
            models = [m.id for m in response.data]
            self._cached_models = models
            return models
        except Exception:
            return []

    def close(self) -> None:
        pass  # openai SDK handles cleanup

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert AIOS Messages to OpenAI message format."""
        result = []
        for msg in messages:
            openai_msg: dict[str, Any] = {"role": msg.role.value, "content": msg.text}
            if msg.tool_calls:
                openai_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            if msg.tool_call_id:
                openai_msg["tool_call_id"] = msg.tool_call_id
            result.append(openai_msg)
        return result
