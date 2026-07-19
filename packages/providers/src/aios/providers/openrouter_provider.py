"""OpenRouter provider — access 200+ models via a unified API.

OpenRouter is OpenAI-compatible, so we wrap OpenAIEngine with
a different base_url and model prefix handling.

Needs: OPENROUTER_API_KEY env var.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from aios.agents.engine import (
    CompletionResult,
    EngineConnectionError,
    InferenceEngine,
    StreamChunk,
    Usage,
)
from aios.agents.registry import EngineRegistry

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from aios.agents.types import Message


@EngineRegistry.register("openrouter")
class OpenRouterEngine(InferenceEngine):
    """OpenRouter inference backend.

    Model format: just use the model name from openrouter.ai/models
    e.g. "meta-llama/llama-3.1-8b-instruct", "mistralai/mistral-7b-instruct"
    """

    name = "openrouter"
    _BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self, *, api_key: str | None = None, model: str = "meta-llama/llama-3.1-8b-instruct"
    ) -> None:
        try:
            import openai  # noqa: F401
        except ImportError as e:
            raise EngineConnectionError("openai package not installed") from e

        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self._default_model = model

        import openai as _openai

        self._client = _openai.AsyncOpenAI(
            api_key=self._api_key or "dummy",
            base_url=self._BASE_URL,
            default_headers={
                "HTTP-Referer": "https://github.com/vimarshakk/aios",
                "X-Title": "AIOS",
            },
        )

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
        import time

        t0 = time.monotonic()
        target_model = model or self._default_model

        openai_messages = [
            {
                "role": m.role.value if hasattr(m.role, "value") else str(m.role),
                "content": m.content,
            }
            for m in messages
        ]

        try:
            response = await self._client.chat.completions.create(
                model=target_model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
            )
            choice = response.choices[0]
            usage_obj = response.usage
            usage = Usage(
                prompt_tokens=usage_obj.prompt_tokens if usage_obj else 0,
                completion_tokens=usage_obj.completion_tokens if usage_obj else 0,
                total_tokens=usage_obj.total_tokens if usage_obj else 0,
            )
            return CompletionResult(
                content=choice.message.content or "",
                usage=usage,
                model=response.model,
                finish_reason=choice.finish_reason or "stop",
                latency_ms=(time.monotonic() - t0) * 1000,
            )
        except Exception as e:
            raise EngineConnectionError(f"OpenRouter call failed: {e}") from e

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        target_model = model or self._default_model
        openai_messages = [
            {
                "role": m.role.value if hasattr(m.role, "value") else str(m.role),
                "content": m.content,
            }
            for m in messages
        ]
        try:
            stream = await self._client.chat.completions.create(
                model=target_model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if not choice:
                    continue
                content = choice.delta.content if choice.delta else None
                finish = choice.finish_reason
                yield StreamChunk(content=content, finish_reason=finish, done=(finish is not None))
        except Exception as e:
            raise EngineConnectionError(f"OpenRouter stream failed: {e}") from e

    async def list_models(self) -> list[str]:
        return [
            "meta-llama/llama-3.1-8b-instruct",
            "meta-llama/llama-3.1-70b-instruct",
            "mistralai/mistral-7b-instruct",
            "anthropic/claude-3-haiku",
            "google/gemini-flash-1.5",
            "deepseek/deepseek-chat",
            "qwen/qwen-2.5-72b-instruct",
        ]


__all__ = ["OpenRouterEngine"]
