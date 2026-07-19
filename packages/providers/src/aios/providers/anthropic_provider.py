"""Anthropic inference engine adapter.

Uses the official anthropic SDK. Requires ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import json
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


@EngineRegistry.register("anthropic")
class AnthropicEngine(InferenceEngine):
    """Anthropic Claude inference backend."""

    name = "anthropic"

    def __init__(self, *, api_key: str | None = None) -> None:
        try:
            import anthropic
        except ImportError as e:
            raise EngineConnectionError("anthropic package not installed") from e

        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = anthropic.AsyncAnthropic(api_key=self._api_key or "dummy")

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

        system_prompt, anthropic_messages = self._convert_messages(messages)

        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            request_kwargs["system"] = system_prompt
        if stop:
            request_kwargs["stop_sequences"] = stop

        # Pass tools if provided
        if "tools" in kwargs:
            request_kwargs["tools"] = kwargs["tools"]

        try:
            response = await self._client.messages.create(**request_kwargs)
        except Exception as e:
            raise EngineConnectionError(f"Anthropic API error: {e}") from e

        content = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=(
                        json.dumps(block.input)
                        if isinstance(block.input, dict)
                        else str(block.input)
                    ),
                ))

        usage = Usage(
            prompt_tokens=response.usage.input_tokens if response.usage else 0,
            completion_tokens=response.usage.output_tokens if response.usage else 0,
            total_tokens=(
                (response.usage.input_tokens + response.usage.output_tokens)
                if response.usage else 0
            ),
        )

        latency_ms = (time.monotonic() - t0) * 1000

        return CompletionResult(
            content=content,
            usage=usage,
            model=response.model,
            finish_reason=response.stop_reason or "stop",
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
        system_prompt, anthropic_messages = self._convert_messages(messages)

        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            request_kwargs["system"] = system_prompt
        if stop:
            request_kwargs["stop_sequences"] = stop

        try:
            async with self._client.messages.stream(**request_kwargs) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(content=text)
                yield StreamChunk(finish_reason="stop", done=True)
        except Exception as e:
            raise EngineConnectionError(f"Anthropic streaming error: {e}") from e

    async def health(self) -> bool:
        try:
            await self._client.messages.create(
                model="claude-3-haiku-20240307",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
            return True
        except Exception:
            return False

    def models(self) -> list[str]:
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
        ]

    def close(self) -> None:
        pass

    def _convert_messages(self, messages: list[Message]) -> tuple[str, list[dict[str, Any]]]:
        """Convert AIOS Messages to Anthropic message format.

        Returns (system_prompt, messages). Anthropic requires system as a separate param.
        """
        system_prompt = ""
        anthropic_messages = []

        for msg in messages:
            if msg.role.value == "system":
                system_prompt = msg.text
                continue

            anthropic_msg: dict[str, Any] = {"role": msg.role.value, "content": msg.text}

            if msg.tool_calls:
                content_blocks = [{"type": "text", "text": msg.text or ""}]
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": args,
                    })
                anthropic_msg["content"] = content_blocks

            if msg.tool_call_id:
                anthropic_msg["content"] = [{
                    "type": "tool_result",
                    "tool_use_id": msg.tool_call_id,
                    "content": msg.text,
                }]

            anthropic_messages.append(anthropic_msg)

        return system_prompt, anthropic_messages
