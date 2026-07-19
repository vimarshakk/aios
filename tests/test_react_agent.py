"""Tests for ReAct agent."""


import pytest

from aios.agents.engine import CompletionResult, InferenceEngine, Usage
from aios.agents.react.agent import ReActAgent
from aios.agents.tools import BaseTool, ToolSpec
from aios.agents.types import Message, Role, ToolResult


class MockEngine(InferenceEngine):
    """A mock inference engine that returns pre-configured responses."""

    def __init__(self, responses: list[str]):
        self._responses = iter(responses)
        self._calls: list[dict] = []

    async def complete(
        self, messages, *, model="", temperature=0.7, max_tokens=1024, **kwargs
    ):
        self._calls.append({"messages": messages, "model": model})
        content = next(self._responses)
        return CompletionResult(
            content=content,
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            model=model,
        )

    async def stream(
        self, messages, *, model="", temperature=0.7, max_tokens=1024, **kwargs
    ):
        result = await self.complete(
            messages, model=model, temperature=temperature, max_tokens=max_tokens
        )
        from aios.agents.engine import StreamChunk
        yield StreamChunk(content=result.content)

    async def health(self):
        return True

    def models(self):
        return []


class EchoTool(BaseTool):
    spec = ToolSpec(
        name="echo",
        description="Echo back the input.",
        parameters={"text": {"type": "string", "description": "Text to echo"}},
        required=["text"],
    )

    async def execute(self, **kwargs) -> ToolResult:
        text = kwargs.get("text", "")
        return ToolResult(tool_name="echo", content=f"Echo: {text}")


class CalcTool(BaseTool):
    spec = ToolSpec(
        name="calculator",
        description="Evaluate math.",
        parameters={"expression": {"type": "string", "description": "Math expression"}},
        required=["expression"],
    )

    async def execute(self, **kwargs) -> ToolResult:
        expr = kwargs.get("expression", "")
        try:
            result = eval(expr)  # noqa: S307
            return ToolResult(tool_name="calculator", content=str(result))
        except Exception as e:
            return ToolResult(tool_name="calculator", content=f"Error: {e}", success=False)


class TestReActAgent:
    def test_construction(self):
        engine = MockEngine(["Final Answer: Hello"])
        agent = ReActAgent(engine=engine, model="test-model")
        assert agent.name == "react"
        assert agent._model == "test-model"

    def test_construction_with_tools(self):
        engine = MockEngine(["Final Answer: Hello"])
        agent = ReActAgent(
            engine=engine,
            model="test-model",
            tools=[EchoTool(), CalcTool()],
        )
        assert "echo" in agent._tools
        assert "calculator" in agent._tools

    def test_describe(self):
        engine = MockEngine(["Final Answer: Hello"])
        agent = ReActAgent(
            engine=engine,
            model="test-model",
            tools=[EchoTool()],
            max_turns=5,
        )
        desc = agent.describe()
        assert desc["name"] == "react"
        assert desc["model"] == "test-model"
        assert "echo" in desc["tools"]
        assert desc["max_turns"] == 5

    def test_parse_final_answer(self):
        engine = MockEngine([])
        agent = ReActAgent(engine=engine, model="test")
        parsed = agent._parse_response(
            "Thought: I know the answer\nFinal Answer: 42"
        )
        assert parsed["thought"] == "I know the answer"
        assert parsed["final_answer"] == "42"
        assert parsed["action"] == ""

    def test_parse_action(self):
        engine = MockEngine([])
        agent = ReActAgent(engine=engine, model="test")
        parsed = agent._parse_response(
            'Thought: I need to calculate\nAction: calculator\nAction Input: {"expression": "2+2"}'
        )
        assert parsed["thought"] == "I need to calculate"
        assert parsed["action"] == "calculator"
        assert parsed["action_input"] == '{"expression": "2+2"}'
        assert parsed["final_answer"] == ""

    def test_parse_no_action_no_final(self):
        engine = MockEngine([])
        agent = ReActAgent(engine=engine, model="test")
        parsed = agent._parse_response("Just some text without structure")
        assert parsed["action"] == ""
        assert parsed["final_answer"] == ""

    @pytest.mark.asyncio
    async def test_direct_final_answer(self):
        engine = MockEngine(["Thought: I know\nFinal Answer: The answer is 42"])
        agent = ReActAgent(engine=engine, model="test")
        result = await agent.run("What is 6*7?")
        assert result == "The answer is 42"

    @pytest.mark.asyncio
    async def test_tool_use_then_final(self):
        engine = MockEngine([
            'Thought: I need to echo\nAction: echo\nAction Input: {"text": "hello"}',
            "Thought: I got the echo\nFinal Answer: The echo said hello",
        ])
        agent = ReActAgent(
            engine=engine,
            model="test",
            tools=[EchoTool()],
        )
        result = await agent.run("Echo hello")
        assert result == "The echo said hello"
        assert len(engine._calls) == 2

    @pytest.mark.asyncio
    async def test_tool_not_found(self):
        engine = MockEngine([
            "Thought: Let me use unknown\nAction: nonexistent\nAction Input: {}",
            "Thought: Tool failed\nFinal Answer: Sorry",
        ])
        agent = ReActAgent(engine=engine, model="test")
        result = await agent.run("Do something")
        assert result == "Sorry"

    @pytest.mark.asyncio
    async def test_max_turns_exceeded(self):
        # Always returns an action, never a final answer
        engine = MockEngine([
            'Thought: Keep going\nAction: echo\nAction Input: {"text": "loop"}',
            'Thought: Still going\nAction: echo\nAction Input: {"text": "loop2"}',
            'Thought: More\nAction: echo\nAction Input: {"text": "loop3"}',
        ])
        agent = ReActAgent(
            engine=engine,
            model="test",
            tools=[EchoTool()],
            max_turns=3,
        )
        result = await agent.run("Loop forever")
        assert "Max turns" in result

    @pytest.mark.asyncio
    async def test_step(self):
        engine = MockEngine(["Just a single response"])
        agent = ReActAgent(engine=engine, model="test")
        messages = [Message(role=Role.USER, content="Hello")]
        msg = await agent.step(messages)
        assert msg.content == "Just a single response"
        assert msg.role == Role.ASSISTANT

    @pytest.mark.asyncio
    async def test_tool_descriptions_in_prompt(self):
        engine = MockEngine(["Final Answer: ok"])
        agent = ReActAgent(
            engine=engine,
            model="test",
            tools=[EchoTool()],
        )
        prompt = agent._build_system_prompt()
        assert "echo" in prompt
        assert "Echo back the input" in prompt
