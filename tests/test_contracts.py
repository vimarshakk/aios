"""Contract tests — verify frozen v1 interfaces haven't changed.

These tests MUST pass before any M2 work begins. If they fail, the
public API has been broken and the change must be reverted or the
interface version bumped.
"""

from __future__ import annotations

import inspect
from importlib import import_module

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_dotted(path: str) -> object:
    """Import 'aios.agents.engine.InferenceEngine' style path."""
    parts = path.rsplit(".", 1)
    module = import_module(parts[0])
    return getattr(module, parts[1])


def _has_method(cls: type, name: str) -> bool:
    return hasattr(cls, name) and callable(getattr(cls, name, None))


# ---------------------------------------------------------------------------
# Version contract
# ---------------------------------------------------------------------------


class TestVersionContracts:
    def test_agents_version(self) -> None:
        from aios.agents import API_VERSION
        assert API_VERSION == "1.0"

    def test_memory_version(self) -> None:
        from aios.memory import API_VERSION
        assert API_VERSION == "1.0"

    def test_context_version(self) -> None:
        from aios.context import API_VERSION
        assert API_VERSION == "1.0"

    def test_workflows_version(self) -> None:
        from aios.workflows import API_VERSION
        assert API_VERSION == "1.0"

    def test_plugins_version(self) -> None:
        from aios.plugins import API_VERSION
        assert API_VERSION == "1.0"

    def test_sdk_version(self) -> None:
        from aios.sdk import API_VERSION
        assert API_VERSION == "1.0"

    def test_gateway_version(self) -> None:
        from aios.gateway import API_VERSION
        assert API_VERSION == "1.0"

    def test_orchestrator_version(self) -> None:
        from aios.orchestrator import API_VERSION
        assert API_VERSION == "1.0"

    def test_versions_registry(self) -> None:
        from aios.versions import check_all_versions
        versions = check_all_versions()
        assert len(versions) >= 8
        for pkg, ver in versions.items():
            assert ver == "1.0", f"{pkg} version is {ver}, expected 1.0"


# ---------------------------------------------------------------------------
# InferenceEngine contract
# ---------------------------------------------------------------------------


class TestInferenceEngineContract:
    def test_importable(self) -> None:
        from aios.agents.engine import InferenceEngine
        assert InferenceEngine is not None

    def test_is_abstract(self) -> None:
        from aios.agents.engine import InferenceEngine
        assert inspect.isabstract(InferenceEngine)

    def test_has_complete(self) -> None:
        from aios.agents.engine import InferenceEngine
        assert _has_method(InferenceEngine, "complete")

    def test_has_stream(self) -> None:
        from aios.agents.engine import InferenceEngine
        assert _has_method(InferenceEngine, "stream")

    def test_has_health(self) -> None:
        from aios.agents.engine import InferenceEngine
        assert _has_method(InferenceEngine, "health")

    def test_has_models(self) -> None:
        from aios.agents.engine import InferenceEngine
        assert _has_method(InferenceEngine, "models")

    def test_has_close(self) -> None:
        from aios.agents.engine import InferenceEngine
        assert _has_method(InferenceEngine, "close")

    def test_has_describe(self) -> None:
        from aios.agents.engine import InferenceEngine
        assert _has_method(InferenceEngine, "describe")

    def test_name_attribute(self) -> None:
        from aios.agents.engine import InferenceEngine
        assert hasattr(InferenceEngine, "name")


# ---------------------------------------------------------------------------
# CompletionResult / Usage / StreamChunk
# ---------------------------------------------------------------------------


class TestCompletionResultContract:
    def test_importable(self) -> None:
        from aios.agents.engine import CompletionResult, StreamChunk, Usage
        assert CompletionResult is not None
        assert StreamChunk is not None
        assert Usage is not None

    def test_usage_fields(self) -> None:
        from aios.agents.engine import Usage
        fields = {f.name for f in Usage.__dataclass_fields__.values()}
        assert "prompt_tokens" in fields
        assert "completion_tokens" in fields
        assert "total_tokens" in fields

    def test_completion_result_fields(self) -> None:
        from aios.agents.engine import CompletionResult
        fields = {f.name for f in CompletionResult.__dataclass_fields__.values()}
        assert "content" in fields
        assert "usage" in fields
        assert "model" in fields
        assert "tool_calls" in fields


# ---------------------------------------------------------------------------
# BaseAgent contract
# ---------------------------------------------------------------------------


class TestBaseAgentContract:
    def test_importable(self) -> None:
        from aios.agents.base import BaseAgent
        assert BaseAgent is not None

    def test_is_abstract(self) -> None:
        from aios.agents.base import BaseAgent
        assert inspect.isabstract(BaseAgent)

    def test_has_run(self) -> None:
        from aios.agents.base import BaseAgent
        assert _has_method(BaseAgent, "run")

    def test_has_step(self) -> None:
        from aios.agents.base import BaseAgent
        assert _has_method(BaseAgent, "step")


# ---------------------------------------------------------------------------
# EventBus contract
# ---------------------------------------------------------------------------


class TestEventBusContract:
    def test_importable(self) -> None:
        from aios.agents.events import EventBus, EventType, get_event_bus
        assert EventBus is not None
        assert EventType is not None
        assert callable(get_event_bus)

    def test_has_subscribe(self) -> None:
        from aios.agents.events import EventBus
        assert _has_method(EventBus, "subscribe")

    def test_has_publish(self) -> None:
        from aios.agents.events import EventBus
        assert _has_method(EventBus, "publish")

    def test_has_history(self) -> None:
        from aios.agents.events import EventBus
        bus = EventBus()
        assert hasattr(bus, "history")

    def test_event_type_values(self) -> None:
        from aios.agents.events import EventType
        required = {"INFERENCE_START", "INFERENCE_END", "TOOL_CALL_START", "TOOL_CALL_END"}
        values = {e.name for e in EventType}
        assert required.issubset(values)


# ---------------------------------------------------------------------------
# MemoryBackend contract
# ---------------------------------------------------------------------------


class TestMemoryBackendContract:
    def test_importable(self) -> None:
        from aios.memory.backend import MemoryBackend, RetrievalResult
        assert MemoryBackend is not None
        assert RetrievalResult is not None

    def test_is_abstract(self) -> None:
        from aios.memory.backend import MemoryBackend
        assert inspect.isabstract(MemoryBackend)

    def test_has_store(self) -> None:
        from aios.memory.backend import MemoryBackend
        assert _has_method(MemoryBackend, "store")

    def test_has_retrieve(self) -> None:
        from aios.memory.backend import MemoryBackend
        assert _has_method(MemoryBackend, "retrieve")

    def test_has_delete(self) -> None:
        from aios.memory.backend import MemoryBackend
        assert _has_method(MemoryBackend, "delete")

    def test_has_clear(self) -> None:
        from aios.memory.backend import MemoryBackend
        assert _has_method(MemoryBackend, "clear")

    def test_has_count(self) -> None:
        from aios.memory.backend import MemoryBackend
        assert _has_method(MemoryBackend, "count")

    def test_retrieval_result_fields(self) -> None:
        from aios.memory.backend import RetrievalResult
        fields = {f.name for f in RetrievalResult.__dataclass_fields__.values()}
        assert "content" in fields
        assert "score" in fields
        assert "metadata" in fields
        assert "source" in fields
        assert "doc_id" in fields


# ---------------------------------------------------------------------------
# HybridMemoryManager contract
# ---------------------------------------------------------------------------


class TestHybridMemoryManagerContract:
    def test_importable(self) -> None:
        from aios.memory.manager import HybridMemoryManager
        assert HybridMemoryManager is not None

    def test_has_register(self) -> None:
        from aios.memory.manager import HybridMemoryManager
        assert _has_method(HybridMemoryManager, "register")

    def test_has_retrieve(self) -> None:
        from aios.memory.manager import HybridMemoryManager
        assert _has_method(HybridMemoryManager, "retrieve")

    def test_has_store(self) -> None:
        from aios.memory.manager import HybridMemoryManager
        assert _has_method(HybridMemoryManager, "store")


# ---------------------------------------------------------------------------
# ContextBuilder contract
# ---------------------------------------------------------------------------


class TestContextBuilderContract:
    def test_importable(self) -> None:
        from aios.context.builder import ContextBuilder, ContextSpec
        assert ContextBuilder is not None
        assert ContextSpec is not None

    def test_has_build(self) -> None:
        from aios.context.builder import ContextBuilder
        assert _has_method(ContextBuilder, "build")

    def test_has_build_simple(self) -> None:
        from aios.context.builder import ContextBuilder
        assert _has_method(ContextBuilder, "build_simple")


# ---------------------------------------------------------------------------
# Workflow contract
# ---------------------------------------------------------------------------


class TestWorkflowContract:
    def test_importable(self) -> None:
        from aios.workflows.base import Workflow, WorkflowResult, WorkflowStep
        assert Workflow is not None
        assert WorkflowStep is not None
        assert WorkflowResult is not None

    def test_step_status_values(self) -> None:
        from aios.workflows.base import StepStatus
        required = {"PENDING", "RUNNING", "COMPLETED", "FAILED"}
        values = {s.name for s in StepStatus}
        assert required.issubset(values)

    def test_executor_importable(self) -> None:
        from aios.workflows.executor import WorkflowExecutor
        assert WorkflowExecutor is not None

    def test_executor_has_run(self) -> None:
        from aios.workflows.executor import WorkflowExecutor
        assert _has_method(WorkflowExecutor, "run")


# ---------------------------------------------------------------------------
# PluginManifest contract
# ---------------------------------------------------------------------------


class TestPluginManifestContract:
    def test_importable(self) -> None:
        from aios.plugins.manifest import PluginManifest, ToolSpec
        assert PluginManifest is not None
        assert ToolSpec is not None

    def test_has_from_yaml(self) -> None:
        from aios.plugins.manifest import PluginManifest
        assert _has_method(PluginManifest, "from_yaml")

    def test_has_from_file(self) -> None:
        from aios.plugins.manifest import PluginManifest
        assert _has_method(PluginManifest, "from_file")

    def test_plugin_runtime_importable(self) -> None:
        from aios.plugins.runtime import PluginRuntime, PluginStatus
        assert PluginRuntime is not None
        assert PluginStatus is not None

    def test_plugin_status_values(self) -> None:
        from aios.plugins.runtime import PluginStatus
        required = {"INSTALLED", "ENABLED", "DISABLED", "ERROR"}
        values = {s.name for s in PluginStatus}
        assert required.issubset(values)


# ---------------------------------------------------------------------------
# Permission contract
# ---------------------------------------------------------------------------


class TestPermissionContract:
    def test_permission_constants(self) -> None:
        from aios.agents.permissions import Permission
        required = {"FILESYSTEM_READ", "NETWORK_HTTP", "PROCESS_EXEC"}
        actual = {name for name in dir(Permission) if name.isupper()}
        assert required.issubset(actual)

    def test_permission_set_importable(self) -> None:
        from aios.agents.permissions import PermissionChecker, PermissionSet
        assert PermissionSet is not None
        assert PermissionChecker is not None

    def test_permission_set_has(self) -> None:
        from aios.agents.permissions import PermissionSet
        ps = PermissionSet(["a", "b"])
        assert ps.has("a") is True
        assert ps.has("c") is False


# ---------------------------------------------------------------------------
# Registry contract
# ---------------------------------------------------------------------------


class TestRegistryContract:
    def test_registry_base_importable(self) -> None:
        from aios.agents.registry import CapabilityRegistry, RegistryBase
        assert RegistryBase is not None
        assert CapabilityRegistry is not None

    def test_capability_registry_has_discover(self) -> None:
        from aios.agents.registry import CapabilityRegistry
        assert _has_method(CapabilityRegistry, "discover")

    def test_capability_registry_has_find(self) -> None:
        from aios.agents.registry import CapabilityRegistry
        assert _has_method(CapabilityRegistry, "find")


# ---------------------------------------------------------------------------
# Gateway contract
# ---------------------------------------------------------------------------


class TestGatewayContract:
    def test_importable(self) -> None:
        from aios.gateway.main import app
        assert app is not None

    def test_has_chat_endpoint(self) -> None:
        from aios.gateway.main import app
        routes = [r.path for r in app.routes]
        assert "/chat" in routes

    def test_has_health_endpoint(self) -> None:
        from aios.gateway.main import app
        routes = [r.path for r in app.routes]
        assert "/health" in routes


# ---------------------------------------------------------------------------
# SDK contract
# ---------------------------------------------------------------------------


class TestSDKContract:
    def test_importable(self) -> None:
        from aios.sdk.client import AiosClient, ChatMessage, ChatResult
        assert AiosClient is not None
        assert ChatMessage is not None
        assert ChatResult is not None

    def test_has_chat(self) -> None:
        from aios.sdk.client import AiosClient
        assert _has_method(AiosClient, "chat")

    def test_has_health(self) -> None:
        from aios.sdk.client import AiosClient
        assert _has_method(AiosClient, "health")


# ---------------------------------------------------------------------------
# Types contract
# ---------------------------------------------------------------------------


class TestTypesContract:
    def test_message_importable(self) -> None:
        from aios.agents.types import Conversation, Message, Role, ToolCall, ToolResult
        assert Message is not None
        assert Role is not None
        assert ToolCall is not None
        assert ToolResult is not None
        assert Conversation is not None

    def test_role_values(self) -> None:
        from aios.agents.types import Role
        required = {"SYSTEM", "USER", "ASSISTANT", "TOOL"}
        values = {r.name for r in Role}
        assert required.issubset(values)

    def test_message_fields(self) -> None:
        from aios.agents.types import Message
        fields = {f.name for f in Message.__dataclass_fields__.values()}
        assert "role" in fields
        assert "content" in fields

    def test_tool_result_fields(self) -> None:
        from aios.agents.types import ToolResult
        fields = {f.name for f in ToolResult.__dataclass_fields__.values()}
        assert "tool_name" in fields
        assert "content" in fields
        assert "success" in fields
