"""Tests for canonical AIOS types."""


from aios.agents.types import (
    Conversation,
    Message,
    ModelSpec,
    Quantization,
    Role,
    RoutingContext,
    StepType,
    ToolCall,
    ToolResult,
    Trace,
    TraceStep,
)


class TestRole:
    def test_role_values(self):
        assert Role.SYSTEM == "system"
        assert Role.USER == "user"
        assert Role.ASSISTANT == "assistant"
        assert Role.TOOL == "tool"

    def test_role_from_string(self):
        assert Role("user") == Role.USER

    def test_role_is_str(self):
        assert isinstance(Role.USER, str)
        assert Role.USER == "user"


class TestQuantization:
    def test_quantization_values(self):
        assert Quantization.NONE == "none"
        assert Quantization.FP8 == "fp8"
        assert Quantization.GGUF == "gguf"

    def test_quantization_from_string(self):
        assert Quantization("int8") == Quantization.INT8


class TestStepType:
    def test_step_type_values(self):
        assert StepType.ROUTE == "route"
        assert StepType.TOOL_CALL == "tool_call"

    def test_step_type_from_string(self):
        assert StepType("generate") == StepType.GENERATE


class TestToolCall:
    def test_construction(self):
        tc = ToolCall(id="tc_1", name="calculator", arguments='{"expression": "2+2"}')
        assert tc.id == "tc_1"
        assert tc.name == "calculator"
        assert tc.arguments == '{"expression": "2+2"}'


class TestMessage:
    def test_construction(self):
        msg = Message(role=Role.USER, content="Hello")
        assert msg.role == Role.USER
        assert msg.content == "Hello"
        assert msg.text == "Hello"

    def test_text_property_when_none(self):
        msg = Message(role=Role.ASSISTANT, content=None)
        assert msg.text == ""

    def test_with_tool_calls(self):
        tc = ToolCall(id="tc_1", name="calc", arguments="{}")
        msg = Message(role=Role.ASSISTANT, tool_calls=[tc])
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1

    def test_with_metadata(self):
        msg = Message(role=Role.USER, content="hi", metadata={"source": "test"})
        assert msg.metadata["source"] == "test"


class TestConversation:
    def test_add_messages(self):
        conv = Conversation()
        conv.add(Message(role=Role.USER, content="Hello"))
        conv.add(Message(role=Role.ASSISTANT, content="Hi"))
        assert len(conv.messages) == 2

    def test_max_messages_limit(self):
        conv = Conversation(max_messages=2)
        conv.add(Message(role=Role.USER, content="msg1"))
        conv.add(Message(role=Role.USER, content="msg2"))
        conv.add(Message(role=Role.USER, content="msg3"))
        assert len(conv.messages) == 2
        assert conv.messages[0].content == "msg2"

    def test_window(self):
        conv = Conversation()
        conv.add(Message(role=Role.USER, content="m1"))
        conv.add(Message(role=Role.USER, content="m2"))
        conv.add(Message(role=Role.USER, content="m3"))
        window = conv.window(2)
        assert len(window) == 2
        assert window[0].content == "m2"

    def test_window_zero(self):
        conv = Conversation()
        conv.add(Message(role=Role.USER, content="m1"))
        assert conv.window(0) == []


class TestModelSpec:
    def test_construction(self):
        spec = ModelSpec(
            model_id="llama3-8b",
            name="Llama 3 8B",
            parameter_count_b=8.0,
            context_length=8192,
        )
        assert spec.model_id == "llama3-8b"
        assert spec.quantization == Quantization.NONE
        assert spec.supported_engines == ()

    def test_with_quantization(self):
        spec = ModelSpec(
            model_id="test",
            name="Test",
            parameter_count_b=1.0,
            context_length=1024,
            quantization=Quantization.FP8,
        )
        assert spec.quantization == Quantization.FP8


class TestToolResult:
    def test_success(self):
        result = ToolResult(tool_name="calc", content="4")
        assert result.success is True
        assert result.cost_usd == 0.0

    def test_failure(self):
        result = ToolResult(tool_name="calc", content="error", success=False)
        assert result.success is False


class TestTraceStep:
    def test_construction(self):
        step = TraceStep(step_type=StepType.ROUTE, timestamp=1000.0)
        assert step.step_type == StepType.ROUTE
        assert step.duration_seconds == 0.0


class TestTrace:
    def test_construction(self):
        trace = Trace(query="hello", agent="default")
        assert trace.query == "hello"
        assert len(trace.trace_id) == 16

    def test_add_step(self):
        trace = Trace()
        step = TraceStep(
            step_type=StepType.ROUTE,
            timestamp=1000.0,
            duration_seconds=0.5,
            output={"tokens": 10},
        )
        trace.add_step(step)
        assert len(trace.steps) == 1
        assert trace.total_latency_seconds == 0.5
        assert trace.total_tokens == 10


class TestRoutingContext:
    def test_defaults(self):
        ctx = RoutingContext(query="hello")
        assert ctx.language == "en"
        assert ctx.urgency == 0.5
        assert ctx.suggested_max_tokens == 1024
