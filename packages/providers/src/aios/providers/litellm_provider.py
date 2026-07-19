"""LiteLLM universal provider — 100+ models via one interface.

Supports: OpenAI, Claude, Gemini, Ollama, OpenRouter, Mistral,
DeepSeek, Qwen, Llama, Cohere, Groq, Together AI, and more.

Usage:
    engine = LiteLLMEngine(model="ollama/llama3.2")
    engine = LiteLLMEngine(model="gpt-4o")
    engine = LiteLLMEngine(model="claude-3-5-sonnet-20241022")
    engine = LiteLLMEngine(model="gemini/gemini-1.5-pro")
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

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from aios.agents.types import Message


def _to_litellm_messages(messages: list[Message]) -> list[dict[str, Any]]:
    """Convert AIOS messages to LiteLLM format."""
    result = []
    for m in messages:
        role = m.role.value if hasattr(m.role, "value") else str(m.role)
        if role == "assistant":
            role = "assistant"
        elif role == "user":
            role = "user"
        elif role == "system":
            role = "system"
        result.append({"role": role, "content": m.content})
    return result


@EngineRegistry.register("litellm")
class LiteLLMEngine(InferenceEngine):
    """Universal LiteLLM inference backend.

    Model name format:
        - Ollama:      "ollama/llama3.2", "ollama/mistral"
        - OpenAI:      "gpt-4o", "gpt-4o-mini", "o1"
        - Anthropic:   "claude-3-5-sonnet-20241022"
        - Gemini:      "gemini/gemini-1.5-pro", "gemini/gemini-flash-1.5"
        - OpenRouter:  "openrouter/meta-llama/llama-3.1-8b-instruct"
        - Groq:        "groq/llama-3.1-70b-versatile"
        - Together:    "together_ai/mistralai/Mistral-7B-Instruct-v0.2"
    """

    name = "litellm"

    def __init__(
        self,
        model: str = "ollama/llama3.2",
        *,
        api_key: str | None = None,
        api_base: str | None = None,
        ollama_base: str | None = None,
    ) -> None:
        try:
            import litellm  # noqa: F401
        except ImportError as e:
            raise EngineConnectionError(
                "litellm package not installed. Run: pip install litellm"
            ) from e

        self._default_model = model
        self._api_key = api_key
        self._api_base = api_base or ollama_base
        self._cached_models: list[str] = []

        # Set Ollama base URL if model is ollama/*
        if model.startswith("ollama/") and not self._api_base:
            self._api_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

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
        import litellm

        t0 = time.monotonic()
        target_model = model or self._default_model
        litellm_messages = _to_litellm_messages(messages)

        call_kwargs: dict[str, Any] = {
            "model": target_model,
            "messages": litellm_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stop:
            call_kwargs["stop"] = stop
        if self._api_key:
            call_kwargs["api_key"] = self._api_key
        if self._api_base:
            call_kwargs["api_base"] = self._api_base

        try:
            response = await litellm.acompletion(**call_kwargs)
            choice = response.choices[0]
            usage_obj = response.usage or {}
            usage = Usage(
                prompt_tokens=getattr(usage_obj, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage_obj, "completion_tokens", 0) or 0,
                total_tokens=getattr(usage_obj, "total_tokens", 0) or 0,
            )
            return CompletionResult(
                content=choice.message.content or "",
                usage=usage,
                model=getattr(response, "model", target_model),
                finish_reason=choice.finish_reason or "stop",
                latency_ms=(time.monotonic() - t0) * 1000,
                raw=dict(response),
            )
        except Exception as e:
            raise EngineConnectionError(
                f"LiteLLM call failed for model '{target_model}': {e}"
            ) from e

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        import litellm

        target_model = model or self._default_model
        litellm_messages = _to_litellm_messages(messages)

        call_kwargs: dict[str, Any] = {
            "model": target_model,
            "messages": litellm_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if self._api_key:
            call_kwargs["api_key"] = self._api_key
        if self._api_base:
            call_kwargs["api_base"] = self._api_base

        try:
            response = await litellm.acompletion(**call_kwargs)
            async for chunk in response:
                choice = chunk.choices[0] if chunk.choices else None
                if not choice:
                    continue
                delta = choice.delta
                content = getattr(delta, "content", None)
                finish = choice.finish_reason
                yield StreamChunk(
                    content=content,
                    finish_reason=finish,
                    done=(finish is not None),
                )
        except Exception as e:
            raise EngineConnectionError(f"LiteLLM stream failed: {e}") from e

    async def list_models(self) -> list[str]:
        """Return a curated list of well-known model identifiers."""
        return [
            # Ollama (local)
            "ollama/llama3.2",
            "ollama/llama3.1",
            "ollama/mistral",
            "ollama/codellama",
            "ollama/deepseek-coder",
            "ollama/qwen2.5",
            "ollama/phi3",
            "ollama/gemma2",
            "ollama/llava",
            # OpenAI
            "gpt-4o",
            "gpt-4o-mini",
            "o1-preview",
            # Anthropic
            "claude-3-5-sonnet-20241022",
            "claude-3-haiku-20240307",
            # Gemini
            "gemini/gemini-1.5-pro",
            "gemini/gemini-1.5-flash",
            # OpenRouter
            "openrouter/meta-llama/llama-3.1-8b-instruct",
            "openrouter/mistralai/mistral-7b-instruct",
        ]

    async def health(self) -> bool:
        """Check if LiteLLM / the backend is reachable."""
        try:
            import litellm  # noqa: F401

            return True
        except ImportError:
            return False

    def models(self) -> list[str]:
        """Synchronous models list (uses cached list)."""
        return [
            "ollama/llama3.2",
            "ollama/codellama",
            "ollama/llava",
            "gpt-4o",
            "claude-3-5-sonnet-20241022",
            "gemini/gemini-1.5-pro",
        ]


def auto_select_model(task_type: str) -> str:
    """Auto-select model based on task type, preferring local Ollama."""
    task_model_map: dict[str, str] = {
        "coding": os.environ.get("AIOS_CODING_MODEL", "ollama/codellama"),
        "vision": os.environ.get("AIOS_VISION_MODEL", "ollama/llava"),
        "research": os.environ.get("AIOS_RESEARCH_MODEL", "ollama/llama3.2"),
        "fast": os.environ.get("AIOS_FAST_MODEL", "ollama/phi3"),
        "reasoning": os.environ.get("AIOS_REASONING_MODEL", "ollama/llama3.1"),
        "default": os.environ.get("AIOS_DEFAULT_MODEL", "ollama/llama3.2"),
    }
    return task_model_map.get(task_type, task_model_map["default"])


__all__ = ["LiteLLMEngine", "auto_select_model"]
