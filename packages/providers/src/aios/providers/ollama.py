"""Ollama inference engine adapter.

Uses the native Ollama HTTP API for optimal performance.
Supports OLLAMA_HOST env var (default: http://localhost:11434).
"""

from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING, Any

import httpx

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


@EngineRegistry.register("ollama")
class OllamaEngine(InferenceEngine):
    """Ollama inference backend using native HTTP API."""

    name = "ollama"

    def __init__(self, *, host: str | None = None, timeout: float = 120.0) -> None:
        self._host = (host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._host, timeout=timeout)
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

        ollama_messages = self._convert_messages(messages)

        body: dict[str, Any] = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if stop:
            body["options"]["stop"] = stop

        # If tools are available in kwargs, pass them for native function calling
        if "tools" in kwargs:
            body["tools"] = kwargs["tools"]

        try:
            resp = await self._client.post("/api/chat", json=body)
            resp.raise_for_status()
        except httpx.ConnectError as e:
            raise EngineConnectionError(f"Cannot connect to Ollama at {self._host}: {e}") from e

        data = resp.json()

        message = data.get("message", {})
        content = message.get("content", "")
        tool_calls = self._parse_tool_calls(message.get("tool_calls", []))

        usage = Usage(
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        )

        latency_ms = (time.monotonic() - t0) * 1000

        return CompletionResult(
            content=content,
            usage=usage,
            model=data.get("model", model),
            finish_reason="stop",
            tool_calls=tool_calls,
            latency_ms=latency_ms,
            raw=data,
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
        ollama_messages = self._convert_messages(messages)

        body: dict[str, Any] = {
            "model": model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if stop:
            body["options"]["stop"] = stop

        try:
            async with self._client.stream("POST", "/api/chat", json=body) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    chunk_data = json.loads(line)

                    if chunk_data.get("done"):
                        usage = Usage(
                            prompt_tokens=chunk_data.get("prompt_eval_count", 0),
                            completion_tokens=chunk_data.get("eval_count", 0),
                            total_tokens=(
                                chunk_data.get("prompt_eval_count", 0)
                                + chunk_data.get("eval_count", 0)
                            ),
                        )
                        yield StreamChunk(
                            finish_reason="stop",
                            usage=usage,
                            done=True,
                        )
                        return

                    message = chunk_data.get("message", {})
                    content = message.get("content", "")
                    if content:
                        yield StreamChunk(content=content)

        except httpx.ConnectError as e:
            raise EngineConnectionError(f"Cannot connect to Ollama at {self._host}: {e}") from e

    async def health(self) -> bool:
        try:
            resp = await self._client.get("/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    def models(self) -> list[str]:
        """List models synchronously (requires cached data)."""
        return self._cached_models

    async def list_models_async(self) -> list[str]:
        """Async model listing. Call once to warm the cache."""
        try:
            resp = await self._client.get("/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            self._cached_models = models
            return models
        except Exception:
            return []

    async def close(self) -> None:
        await self._client.aclose()

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert AIOS Messages to Ollama message format."""
        result = []
        for msg in messages:
            ollama_msg: dict[str, Any] = {"role": msg.role.value, "content": msg.text}
            if msg.tool_calls:
                ollama_msg["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        }
                    }
                    for tc in msg.tool_calls
                ]
            if msg.tool_call_id:
                ollama_msg["tool_call_id"] = msg.tool_call_id
            result.append(ollama_msg)
        return result

    def _parse_tool_calls(self, raw_tool_calls: list[dict[str, Any]]) -> list[ToolCall]:
        """Parse Ollama tool_calls into AIOS ToolCall objects."""
        tool_calls = []
        for i, tc in enumerate(raw_tool_calls):
            func = tc.get("function", {})
            name = func.get("name", "")
            args = func.get("arguments", "{}")
            if isinstance(args, dict):
                args = json.dumps(args)
            tool_calls.append(ToolCall(id=f"ollama_{i}", name=name, arguments=args))
        return tool_calls
