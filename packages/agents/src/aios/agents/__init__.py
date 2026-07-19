# M2.1 — Multi-agent execution
from aios.agents.aggregator import ResultAggregator
from aios.agents.engine import (
    CompletionResult,
    EngineConnectionError,
    EngineContextLengthError,
    EngineError,
    InferenceEngine,
    StreamChunk,
    Usage,
)
from aios.agents.events import Event, EventBus, EventType, get_event_bus
from aios.agents.multi_executor import MultiAgentExecutor, SubtaskResult
from aios.agents.pool import AgentEntry, AgentPool
from aios.agents.registry import AgentRegistry, EngineRegistry, RegistryBase, ToolRegistry
from aios.agents.task import Subtask, TaskDecomposer, resolve_execution_order
from aios.agents.types import (
    Conversation,
    Message,
    ModelSpec,
    Quantization,
    Role,
    StepType,
    ToolCall,
    ToolResult,
)

API_VERSION = "1.0"

__all__ = [
    # M2.1
    "AgentEntry",
    "AgentPool",
    "AgentRegistry",
    "CompletionResult",
    "Conversation",
    "EngineConnectionError",
    "EngineContextLengthError",
    "EngineError",
    "EngineRegistry",
    "Event",
    "EventBus",
    "EventType",
    "InferenceEngine",
    "Message",
    "ModelSpec",
    "MultiAgentExecutor",
    "Quantization",
    "RegistryBase",
    "ResultAggregator",
    "Role",
    "StepType",
    "StreamChunk",
    "Subtask",
    "SubtaskResult",
    "TaskDecomposer",
    "ToolCall",
    "ToolRegistry",
    "ToolResult",
    "Usage",
    "get_event_bus",
    "resolve_execution_order",
]
