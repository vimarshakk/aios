"""Canonical data types shared across all AIOS primitives."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Quantization(StrEnum):
    NONE = "none"
    FP8 = "fp8"
    FP4 = "fp4"
    INT8 = "int8"
    INT4 = "int4"
    GGUF = "gguf"
    GGUF_Q4 = "gguf_q4"
    GGUF_Q8 = "gguf_q8"


class StepType(StrEnum):
    ROUTE = "route"
    RETRIEVE = "retrieve"
    GENERATE = "generate"
    TOOL_CALL = "tool_call"
    RESPOND = "respond"


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON string


@dataclass(slots=True)
class Message:
    role: Role
    content: str | None = ""
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    images: list[str] | None = None  # base64-encoded for vision models

    @property
    def text(self) -> str:
        return self.content or ""


@dataclass(slots=True)
class Conversation:
    messages: list[Message] = field(default_factory=list)
    max_messages: int | None = None

    def add(self, message: Message) -> None:
        self.messages.append(message)
        if self.max_messages is not None and len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def window(self, n: int) -> list[Message]:
        if n <= 0:
            return []
        return self.messages[-n:]


@dataclass(slots=True)
class ModelSpec:
    model_id: str
    name: str
    parameter_count_b: float
    context_length: int
    active_parameter_count_b: float | None = None
    quantization: Quantization = Quantization.NONE
    min_vram_gb: float = 0.0
    supported_engines: Sequence[str] = ()
    provider: str = ""
    requires_api_key: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    tool_name: str
    content: str
    success: bool = True
    usage: dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0
    latency_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TraceStep:
    step_type: StepType
    timestamp: float
    duration_seconds: float = 0.0
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Trace:
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    query: str = ""
    agent: str = ""
    model: str = ""
    engine: str = ""
    steps: list[TraceStep] = field(default_factory=list)
    result: str = ""
    outcome: str | None = None
    feedback: float | None = None
    started_at: float = 0.0
    ended_at: float = 0.0
    total_tokens: int = 0
    total_latency_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)

    def add_step(self, step: TraceStep) -> None:
        self.steps.append(step)
        self.total_latency_seconds += step.duration_seconds
        self.total_tokens += step.output.get("tokens", 0)


@dataclass(slots=True)
class RoutingContext:
    query: str = ""
    query_length: int = 0
    has_code: bool = False
    has_math: bool = False
    has_reasoning: bool = False
    language: str = "en"
    urgency: float = 0.5
    complexity_score: float = 0.0
    suggested_max_tokens: int = 1024
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "Conversation",
    "Message",
    "ModelSpec",
    "Quantization",
    "Role",
    "RoutingContext",
    "StepType",
    "ToolCall",
    "ToolResult",
    "Trace",
    "TraceStep",
]
