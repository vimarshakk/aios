"""Tests for inference engine providers (mocked HTTP)."""


from unittest.mock import AsyncMock, MagicMock

import pytest

from aios.agents.engine import CompletionResult, InferenceEngine, StreamChunk, Usage
from aios.agents.types import Message, Role, ToolCall
from aios.providers.factory import create_engine, list_engines

# ---------------------------------------------------------------------------
# Ollama tests
# ---------------------------------------------------------------------------

class TestOllamaEngine:
    def _make_engine(self):
        from aios.providers.ollama import OllamaEngine
        return OllamaEngine(host="http://localhost:11434")

    def test_create(self):
        engine = self._make_engine()
        assert engine.name == "ollama"

    def test_create_via_factory(self):
        engine = create_engine("ollama")
        assert engine.name == "ollama"

    @pytest.mark.asyncio
    async def test_complete_returns_result(self):
        engine = self._make_engine()
        messages = [Message(role=Role.USER, content="Hello")]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "llama3.2",
            "message": {"content": "Hi there!", "role": "assistant"},
            "prompt_eval_count": 10,
            "eval_count": 5,
            "done": True,
        }
        mock_response.raise_for_status = MagicMock()

        engine._client = MagicMock()
        engine._client.post = AsyncMock(return_value=mock_response)

        result = await engine.complete(messages, model="llama3.2")

        assert isinstance(result, CompletionResult)
        assert result.content == "Hi there!"
        assert result.model == "llama3.2"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 5
        assert result.usage.total_tokens == 15

    @pytest.mark.asyncio
    async def test_complete_with_tool_calls(self):
        engine = self._make_engine()
        messages = [Message(role=Role.USER, content="Calculate 2+2")]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "llama3.2",
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "calculator",
                            "arguments": {"expression": "2+2"},
                        }
                    }
                ],
            },
            "prompt_eval_count": 10,
            "eval_count": 5,
        }
        mock_response.raise_for_status = MagicMock()

        engine._client = MagicMock()
        engine._client.post = AsyncMock(return_value=mock_response)

        result = await engine.complete(messages, model="llama3.2")

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "calculator"
        assert "2+2" in result.tool_calls[0].arguments

    @pytest.mark.asyncio
    async def test_health_success(self):
        engine = self._make_engine()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        engine._client = MagicMock()
        engine._client.get = AsyncMock(return_value=mock_response)

        assert await engine.health() is True

    @pytest.mark.asyncio
    async def test_health_failure(self):
        engine = self._make_engine()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = MagicMock(side_effect=Exception("Server error"))

        engine._client = MagicMock()
        engine._client.get = AsyncMock(return_value=mock_response)

        assert await engine.health() is False

    def test_convert_messages(self):
        engine = self._make_engine()
        messages = [
            Message(role=Role.SYSTEM, content="You are helpful."),
            Message(role=Role.USER, content="Hello"),
            Message(role=Role.ASSISTANT, content="Hi!"),
        ]
        result = engine._convert_messages(messages)
        assert len(result) == 3
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are helpful."
        assert result[1]["role"] == "user"

    def test_parse_tool_calls(self):
        engine = self._make_engine()
        raw = [{"function": {"name": "calc", "arguments": {"x": 1}}}]
        result = engine._parse_tool_calls(raw)
        assert len(result) == 1
        assert result[0].name == "calc"
        assert isinstance(result[0].arguments, str)

    def test_list_engines(self):
        engines = list_engines()
        assert "ollama" in engines
        assert "openai" in engines
        assert "anthropic" in engines


# ---------------------------------------------------------------------------
# OpenAI tests
# ---------------------------------------------------------------------------

class TestOpenAIEngine:
    def _make_engine(self):
        from aios.providers.openai_provider import OpenAIEngine
        return OpenAIEngine(api_key="test-key")

    def test_create(self):
        engine = self._make_engine()
        assert engine.name == "openai"

    def test_create_via_factory(self):
        engine = create_engine("openai", api_key="test-key")
        assert engine.name == "openai"

    @pytest.mark.asyncio
    async def test_convert_messages(self):
        engine = self._make_engine()
        messages = [
            Message(role=Role.USER, content="Hello"),
            Message(
                role=Role.ASSISTANT,
                content="",
                tool_calls=[ToolCall(id="tc1", name="calc", arguments='{"x":1}')],
            ),
            Message(role=Role.TOOL, content="42", tool_call_id="tc1"),
        ]
        result = engine._convert_messages(messages)
        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert len(result[1]["tool_calls"]) == 1
        assert result[1]["tool_calls"][0]["id"] == "tc1"
        assert result[2]["role"] == "tool"
        assert result[2]["tool_call_id"] == "tc1"

    def test_models_list(self):
        engine = self._make_engine()
        # Models starts empty, but async listing works
        assert isinstance(engine.models(), list)


# ---------------------------------------------------------------------------
# Anthropic tests
# ---------------------------------------------------------------------------

class TestAnthropicEngine:
    def _make_engine(self):
        from aios.providers.anthropic_provider import AnthropicEngine
        return AnthropicEngine(api_key="test-key")

    def test_create(self):
        engine = self._make_engine()
        assert engine.name == "anthropic"

    def test_create_via_factory(self):
        engine = create_engine("anthropic", api_key="test-key")
        assert engine.name == "anthropic"

    @pytest.mark.asyncio
    async def test_convert_messages_system(self):
        engine = self._make_engine()
        messages = [
            Message(role=Role.SYSTEM, content="Be helpful."),
            Message(role=Role.USER, content="Hello"),
        ]
        system, anthropic_msgs = engine._convert_messages(messages)
        assert system == "Be helpful."
        assert len(anthropic_msgs) == 1
        assert anthropic_msgs[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_convert_messages_tool_result(self):
        engine = self._make_engine()
        messages = [
            Message(role=Role.USER, content="Calc 2+2"),
            Message(
                role=Role.ASSISTANT,
                content="",
                tool_calls=[ToolCall(id="tc1", name="calc", arguments="{}")],
            ),
            Message(role=Role.TOOL, content="4", tool_call_id="tc1"),
        ]
        system, anthropic_msgs = engine._convert_messages(messages)
        assert system == ""
        # Tool result message should be in Anthropic format
        tool_msg = anthropic_msgs[-1]
        assert tool_msg["role"] == "tool"
        assert isinstance(tool_msg["content"], list)
        assert tool_msg["content"][0]["type"] == "tool_result"
        assert tool_msg["content"][0]["tool_use_id"] == "tc1"

    def test_models_list(self):
        engine = self._make_engine()
        models = engine.models()
        assert len(models) > 0
        assert any("claude" in m for m in models)


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------

class TestEngineFactory:
    @pytest.mark.asyncio
    async def test_create_ollama(self):
        engine = create_engine("ollama")
        assert isinstance(engine, InferenceEngine)
        assert engine.name == "ollama"
        await engine.close()

    def test_create_openai(self):
        engine = create_engine("openai", api_key="test")
        assert isinstance(engine, InferenceEngine)
        assert engine.name == "openai"

    def test_create_anthropic(self):
        engine = create_engine("anthropic", api_key="test")
        assert isinstance(engine, InferenceEngine)
        assert engine.name == "anthropic"

    def test_create_unknown(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            create_engine("nonexistent")

    def test_list_engines(self):
        engines = list_engines()
        assert "ollama" in engines
        assert "openai" in engines
        assert "anthropic" in engines


# ---------------------------------------------------------------------------
# Usage / CompletionResult / StreamChunk type tests
# ---------------------------------------------------------------------------

class TestEngineTypes:
    def test_usage_defaults(self):
        usage = Usage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_completion_result(self):
        result = CompletionResult(
            content="Hello",
            usage=Usage(prompt_tokens=5, completion_tokens=3, total_tokens=8),
            model="test-model",
            finish_reason="stop",
        )
        assert result.content == "Hello"
        assert result.usage.total_tokens == 8
        assert result.model == "test-model"
        assert result.finish_reason == "stop"

    def test_stream_chunk(self):
        chunk = StreamChunk(content="token", done=False)
        assert chunk.content == "token"
        assert chunk.done is False

        done_chunk = StreamChunk(finish_reason="stop", done=True)
        assert done_chunk.done is True
        assert done_chunk.finish_reason == "stop"
