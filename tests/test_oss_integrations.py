"""OSS Integration Tests — tests for all 8 upstream OSS adapters.

Tests each adapter's:
- Lifecycle (connect/disconnect/health_check)
- All exposed actions
- Availability detection
- Error handling when upstream is unavailable
- Connector bindings
- Registry integration
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from aios.integrations.types import IntegrationConfig, IntegrationStatus


# ─── Helper ──────────────────────────────────────────────────────────────────

def make_config(name: str) -> IntegrationConfig:
    return IntegrationConfig(name=name, metadata={})


# ─── Availability Detection ──────────────────────────────────────────────────

class TestOSSAvailability:
    """Each adapter reports availability based on upstream package."""

    def test_openjarvis_availability(self):
        from aios.integrations.oss.openjarvis import OpenJarvisIntegration
        integ = OpenJarvisIntegration(make_config("openjarvis"))
        assert isinstance(integ.is_available, bool)

    def test_openhands_availability(self):
        from aios.integrations.oss.openhands import OpenHandsIntegration
        integ = OpenHandsIntegration(make_config("openhands"))
        assert isinstance(integ.is_available, bool)

    def test_openinterpreter_availability(self):
        from aios.integrations.oss.openinterpreter import OpenInterpreterIntegration
        integ = OpenInterpreterIntegration(make_config("openinterpreter"))
        assert isinstance(integ.is_available, bool)

    def test_anythingllm_availability(self):
        from aios.integrations.oss.anythingllm import AnythingLLMIntegration
        integ = AnythingLLMIntegration(make_config("anythingllm"))
        assert isinstance(integ.is_available, bool)

    def test_librechat_availability(self):
        from aios.integrations.oss.librechat import LibreChatIntegration
        integ = LibreChatIntegration(make_config("librechat"))
        assert isinstance(integ.is_available, bool)

    def test_openwebui_availability(self):
        from aios.integrations.oss.openwebui import OpenWebUIIntegration
        integ = OpenWebUIIntegration(make_config("openwebui"))
        assert isinstance(integ.is_available, bool)

    def test_continue_availability(self):
        from aios.integrations.oss.continue_dev import ContinueIntegration
        integ = ContinueIntegration(make_config("continue"))
        assert isinstance(integ.is_available, bool)

    def test_jan_availability(self):
        from aios.integrations.oss.jan import JanIntegration
        integ = JanIntegration(make_config("jan"))
        assert isinstance(integ.is_available, bool)


# ─── Lifecycle ───────────────────────────────────────────────────────────────

class TestOSSLifecycle:
    """Each adapter follows the Integration lifecycle contract."""

    def test_all_adapters_start_discovered(self):
        from aios.integrations.oss.openjarvis import OpenJarvisIntegration
        from aios.integrations.oss.openhands import OpenHandsIntegration
        from aios.integrations.oss.openinterpreter import OpenInterpreterIntegration
        from aios.integrations.oss.anythingllm import AnythingLLMIntegration
        from aios.integrations.oss.librechat import LibreChatIntegration
        from aios.integrations.oss.openwebui import OpenWebUIIntegration
        from aios.integrations.oss.continue_dev import ContinueIntegration
        from aios.integrations.oss.jan import JanIntegration

        for cls in [
            OpenJarvisIntegration, OpenHandsIntegration,
            OpenInterpreterIntegration, AnythingLLMIntegration,
            LibreChatIntegration, OpenWebUIIntegration,
            ContinueIntegration, JanIntegration,
        ]:
            integ = cls(make_config("test"))
            assert integ.status == IntegrationStatus.DISCOVERED
            assert not integ.is_connected
            assert integ.uptime_seconds == 0.0

    @pytest.mark.asyncio
    async def test_health_check_when_unavailable(self):
        from aios.integrations.oss.openjarvis import OpenJarvisIntegration
        integ = OpenJarvisIntegration(make_config("openjarvis"))
        result = await integ.health_check()
        assert result.healthy is False

    @pytest.mark.asyncio
    async def test_execute_when_unavailable_returns_error(self):
        from aios.integrations.oss.openjarvis import OpenJarvisIntegration
        integ = OpenJarvisIntegration(make_config("openjarvis"))
        result = await integ.execute("execute_workflow", workflow_name="test")
        assert result.ok is False
        assert "not installed" in result.error

    @pytest.mark.asyncio
    async def test_execute_unknown_action_returns_error(self):
        from aios.integrations.oss.openjarvis import OpenJarvisIntegration
        integ = OpenJarvisIntegration(make_config("openjarvis"))
        integ._oj = True  # Force available
        result = await integ.execute("nonexistent_action")
        assert result.ok is False
        assert "Unknown action" in result.error


# ─── OpenJarvis Actions ──────────────────────────────────────────────────────

class TestOpenJarvis:
    @pytest.fixture
    def integ(self):
        from aios.integrations.oss.openjarvis import OpenJarvisIntegration
        i = OpenJarvisIntegration(make_config("openjarvis"))
        i._oj = True  # Force available
        return i

    @pytest.mark.asyncio
    async def test_execute_workflow(self, integ):
        result = await integ.execute("execute_workflow", workflow_name="test_wf", input_data={"x": 1})
        assert result.ok is True
        assert result.data["workflow"] == "test_wf"
        assert result.data["upstream"] == "openjarvis"

    @pytest.mark.asyncio
    async def test_schedule_task(self, integ):
        result = await integ.execute("schedule_task", task_name="my_task", delay_seconds=60)
        assert result.ok is True
        assert result.data["task"] == "my_task"

    @pytest.mark.asyncio
    async def test_evaluate(self, integ):
        result = await integ.execute("evaluate", metric="accuracy", output="pred", expected="gold")
        assert result.ok is True
        assert result.data["metric"] == "accuracy"

    @pytest.mark.asyncio
    async def test_reason(self, integ):
        result = await integ.execute("reason", prompt="Why?", strategy="chain_of_thought")
        assert result.ok is True
        assert result.data["strategy"] == "chain_of_thought"

    @pytest.mark.asyncio
    async def test_list_workflows(self, integ):
        result = await integ.execute("list_workflows")
        assert result.ok is True
        assert "workflows" in result.data

    @pytest.mark.asyncio
    async def test_list_evaluators(self, integ):
        result = await integ.execute("list_evaluators")
        assert result.ok is True
        assert "evaluators" in result.data


# ─── OpenHands Actions ───────────────────────────────────────────────────────

class TestOpenHands:
    @pytest.fixture
    def integ(self):
        from aios.integrations.oss.openhands import OpenHandsIntegration
        i = OpenHandsIntegration(make_config("openhands"))
        i._oh = True
        return i

    @pytest.mark.asyncio
    async def test_run_sandbox(self, integ):
        result = await integ.execute("run_sandbox", code="print('hi')", language="python")
        assert result.ok is True
        assert result.data["language"] == "python"

    @pytest.mark.asyncio
    async def test_git_operation(self, integ):
        result = await integ.execute("git_operation", operation="status", repo_path="/repo")
        assert result.ok is True
        assert result.data["operation"] == "status"

    @pytest.mark.asyncio
    async def test_edit_repository(self, integ):
        result = await integ.execute("edit_repository", task="fix bug", repo_path="/repo")
        assert result.ok is True
        assert result.data["task"] == "fix bug"

    @pytest.mark.asyncio
    async def test_browse_url(self, integ):
        result = await integ.execute("browse_url", url="https://example.com")
        assert result.ok is True
        assert result.data["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_run_task(self, integ):
        result = await integ.execute("run_task", task="refactor auth", repo_path="/repo")
        assert result.ok is True
        assert result.data["task"] == "refactor auth"

    @pytest.mark.asyncio
    async def test_list_sessions(self, integ):
        result = await integ.execute("list_sessions")
        assert result.ok is True
        assert "sessions" in result.data


# ─── Open Interpreter Actions ────────────────────────────────────────────────

class TestOpenInterpreter:
    @pytest.fixture
    def integ(self):
        from aios.integrations.oss.openinterpreter import OpenInterpreterIntegration
        i = OpenInterpreterIntegration(make_config("openinterpreter"))
        i._oi = True
        return i

    @pytest.mark.asyncio
    async def test_run_shell(self, integ):
        result = await integ.execute("run_shell", command="ls -la")
        assert result.ok is True
        assert result.data["command"] == "ls -la"

    @pytest.mark.asyncio
    async def test_run_python(self, integ):
        result = await integ.execute("run_python", code="print(42)")
        assert result.ok is True
        assert result.data["code"] == "print(42)"

    @pytest.mark.asyncio
    async def test_desktop_automate(self, integ):
        result = await integ.execute("desktop_automate", desktop_action="open_browser")
        assert result.ok is True
        assert result.data["action"] == "open_browser"

    @pytest.mark.asyncio
    async def test_file_read(self, integ):
        result = await integ.execute("file_read", path="/tmp/test.txt")
        assert result.ok is True
        assert result.data["path"] == "/tmp/test.txt"

    @pytest.mark.asyncio
    async def test_file_write(self, integ):
        result = await integ.execute("file_write", path="/tmp/out.txt", content="hello")
        assert result.ok is True
        assert result.data["bytes_written"] == 5

    @pytest.mark.asyncio
    async def test_file_list(self, integ):
        result = await integ.execute("file_list", path="/tmp")
        assert result.ok is True
        assert result.data["path"] == "/tmp"

    @pytest.mark.asyncio
    async def test_chat(self, integ):
        result = await integ.execute("chat", message="open chrome")
        assert result.ok is True
        assert result.data["message"] == "open chrome"


# ─── AnythingLLM Actions ─────────────────────────────────────────────────────

class TestAnythingLLM:
    @pytest.fixture
    def integ(self):
        from aios.integrations.oss.anythingllm import AnythingLLMIntegration
        i = AnythingLLMIntegration(make_config("anythingllm"))
        i._base_url = "http://localhost:3001"
        return i

    @pytest.mark.asyncio
    async def test_ingest_document(self, integ):
        result = await integ.execute("ingest_document", workspace="ws1", doc_path="/doc.pdf")
        assert result.ok is True
        assert result.data["workspace"] == "ws1"

    @pytest.mark.asyncio
    async def test_embed(self, integ):
        result = await integ.execute("embed", text="hello world")
        assert result.ok is True
        assert result.data["text"] == "hello world"

    @pytest.mark.asyncio
    async def test_retrieve(self, integ):
        result = await integ.execute("retrieve", query="search term", workspace="ws1", top_k=3)
        assert result.ok is True
        assert result.data["top_k"] == 3

    @pytest.mark.asyncio
    async def test_rag_query(self, integ):
        result = await integ.execute("rag_query", query="what is X", workspace="ws1")
        assert result.ok is True
        assert result.data["query"] == "what is X"

    @pytest.mark.asyncio
    async def test_list_workspaces(self, integ):
        result = await integ.execute("list_workspaces")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_list_documents(self, integ):
        result = await integ.execute("list_documents", workspace="ws1")
        assert result.ok is True
        assert result.data["workspace"] == "ws1"

    @pytest.mark.asyncio
    async def test_delete_document(self, integ):
        result = await integ.execute("delete_document", doc_name="doc.pdf", workspace="ws1")
        assert result.ok is True
        assert result.data["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_configure(self, integ):
        result = await integ.execute("configure", base_url="http://new:3001")
        assert result.ok is True
        assert result.data["base_url"] == "http://new:3001"


# ─── LibreChat Actions ───────────────────────────────────────────────────────

class TestLibreChat:
    @pytest.fixture
    def integ(self):
        from aios.integrations.oss.librechat import LibreChatIntegration
        i = LibreChatIntegration(make_config("librechat"))
        i._lc = True
        return i

    @pytest.mark.asyncio
    async def test_create_conversation(self, integ):
        result = await integ.execute("create_conversation", title="Chat 1", model="gpt-4")
        assert result.ok is True
        assert result.data["title"] == "Chat 1"

    @pytest.mark.asyncio
    async def test_send_message(self, integ):
        result = await integ.execute("send_message", conversation_id="c1", message="hello")
        assert result.ok is True
        assert result.data["message"] == "hello"

    @pytest.mark.asyncio
    async def test_get_conversation(self, integ):
        result = await integ.execute("get_conversation", conversation_id="c1")
        assert result.ok is True
        assert result.data["conversation_id"] == "c1"

    @pytest.mark.asyncio
    async def test_list_conversations(self, integ):
        result = await integ.execute("list_conversations")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_render_markdown(self, integ):
        result = await integ.execute("render_markdown", content="# Hello")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_create_artifact(self, integ):
        result = await integ.execute("create_artifact", type="code", content="print()")
        assert result.ok is True
        assert result.data["type"] == "code"

    @pytest.mark.asyncio
    async def test_get_artifact(self, integ):
        result = await integ.execute("get_artifact", artifact_id="a1")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_list_artifacts(self, integ):
        result = await integ.execute("list_artifacts", conversation_id="c1")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_create_session(self, integ):
        result = await integ.execute("create_session", user_id="u1")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_get_session(self, integ):
        result = await integ.execute("get_session", session_id="s1")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_end_session(self, integ):
        result = await integ.execute("end_session", session_id="s1")
        assert result.ok is True
        assert result.data["status"] == "ended"


# ─── Open WebUI Actions ──────────────────────────────────────────────────────

class TestOpenWebUI:
    @pytest.fixture
    def integ(self):
        from aios.integrations.oss.openwebui import OpenWebUIIntegration
        i = OpenWebUIIntegration(make_config("openwebui"))
        i._base_url = "http://localhost:8080"
        return i

    @pytest.mark.asyncio
    async def test_list_models(self, integ):
        result = await integ.execute("list_models")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_get_model(self, integ):
        result = await integ.execute("get_model", model_id="m1")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_download_model(self, integ):
        result = await integ.execute("download_model", model_name="llama3")
        assert result.ok is True
        assert result.data["model_name"] == "llama3"

    @pytest.mark.asyncio
    async def test_delete_model(self, integ):
        result = await integ.execute("delete_model", model_id="m1")
        assert result.ok is True
        assert result.data["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_configure_provider(self, integ):
        result = await integ.execute("configure_provider", provider="ollama", settings={"url": "http://localhost"})
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_list_providers(self, integ):
        result = await integ.execute("list_providers")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_inference(self, integ):
        result = await integ.execute("inference", model="llama3", prompt="Hello")
        assert result.ok is True
        assert result.data["model"] == "llama3"

    @pytest.mark.asyncio
    async def test_list_pipelines(self, integ):
        result = await integ.execute("list_pipelines")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_get_pipeline(self, integ):
        result = await integ.execute("get_pipeline", pipeline_id="p1")
        assert result.ok is True


# ─── Continue Actions ────────────────────────────────────────────────────────

class TestContinue:
    @pytest.fixture
    def integ(self):
        from aios.integrations.oss.continue_dev import ContinueIntegration
        i = ContinueIntegration(make_config("continue"))
        i._cont = True
        return i

    @pytest.mark.asyncio
    async def test_index_codebase(self, integ):
        result = await integ.execute("index_codebase", workspace="/repo")
        assert result.ok is True
        assert result.data["workspace"] == "/repo"

    @pytest.mark.asyncio
    async def test_autocomplete(self, integ):
        result = await integ.execute("autocomplete", file_path="main.py", line=10, prefix="def ")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_chat(self, integ):
        result = await integ.execute("chat", message="explain this function")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_edit_code(self, integ):
        result = await integ.execute("edit_code", file_path="main.py", instruction="add error handling")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_get_definitions(self, integ):
        result = await integ.execute("get_definitions", symbol="my_func", file_path="main.py")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_get_references(self, integ):
        result = await integ.execute("get_references", symbol="my_func")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_run_mcp(self, integ):
        result = await integ.execute("run_mcp", tool_name="search", params={"q": "test"})
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_list_mcp_tools(self, integ):
        result = await integ.execute("list_mcp_tools")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_get_context(self, integ):
        result = await integ.execute("get_context", query="auth module")
        assert result.ok is True


# ─── Jan Actions ─────────────────────────────────────────────────────────────

class TestJan:
    @pytest.fixture
    def integ(self):
        from aios.integrations.oss.jan import JanIntegration
        i = JanIntegration(make_config("jan"))
        i._jan = True
        return i

    @pytest.mark.asyncio
    async def test_list_models(self, integ):
        result = await integ.execute("list_models")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_get_model(self, integ):
        result = await integ.execute("get_model", model_id="m1")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_download_model(self, integ):
        result = await integ.execute("download_model", model_id="llama3-8b")
        assert result.ok is True
        assert result.data["model_id"] == "llama3-8b"

    @pytest.mark.asyncio
    async def test_delete_model(self, integ):
        result = await integ.execute("delete_model", model_id="m1")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_update_model(self, integ):
        result = await integ.execute("update_model", model_id="m1")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_start_model(self, integ):
        result = await integ.execute("start_model", model_id="m1")
        assert result.ok is True
        assert result.data["status"] == "running"

    @pytest.mark.asyncio
    async def test_stop_model(self, integ):
        result = await integ.execute("stop_model", model_id="m1")
        assert result.ok is True
        assert result.data["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_list_engines(self, integ):
        result = await integ.execute("list_engines")
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_configure_engine(self, integ):
        result = await integ.execute("configure_engine", engine="llama.cpp", settings={"threads": 4})
        assert result.ok is True


# ─── Connector Bindings ──────────────────────────────────────────────────────

class TestOSSConnectors:
    """Each connector declares the correct capabilities."""

    def test_openjarvis_connector_capabilities(self):
        from aios.integrations.oss.openjarvis import OpenJarvisIntegration
        from aios.integrations.oss.connectors import OpenJarvisConnector
        integ = OpenJarvisIntegration(make_config("openjarvis"))
        conn = OpenJarvisConnector(integ)
        caps = conn.capabilities()
        assert "workflow.execute" in caps
        assert "evaluation.run" in caps
        assert "reasoning.invoke" in caps

    def test_openhands_connector_capabilities(self):
        from aios.integrations.oss.openhands import OpenHandsIntegration
        from aios.integrations.oss.connectors import OpenHandsConnector
        integ = OpenHandsIntegration(make_config("openhands"))
        conn = OpenHandsConnector(integ)
        caps = conn.capabilities()
        assert "coding.sandbox" in caps
        assert "coding.git" in caps
        assert "coding.run_task" in caps

    def test_openinterpreter_connector_capabilities(self):
        from aios.integrations.oss.openinterpreter import OpenInterpreterIntegration
        from aios.integrations.oss.connectors import OpenInterpreterConnector
        integ = OpenInterpreterIntegration(make_config("openinterpreter"))
        conn = OpenInterpreterConnector(integ)
        caps = conn.capabilities()
        assert "desktop.shell" in caps
        assert "desktop.python" in caps
        assert "desktop.automate" in caps

    def test_anythingllm_connector_capabilities(self):
        from aios.integrations.oss.anythingllm import AnythingLLMIntegration
        from aios.integrations.oss.connectors import AnythingLLMConnector
        integ = AnythingLLMIntegration(make_config("anythingllm"))
        conn = AnythingLLMConnector(integ)
        caps = conn.capabilities()
        assert "rag.ingest" in caps
        assert "rag.retrieve" in caps
        assert "rag.query" in caps

    def test_librechat_connector_capabilities(self):
        from aios.integrations.oss.librechat import LibreChatIntegration
        from aios.integrations.oss.connectors import LibreChatConnector
        integ = LibreChatIntegration(make_config("librechat"))
        conn = LibreChatConnector(integ)
        caps = conn.capabilities()
        assert "conversation.create" in caps
        assert "artifact.create" in caps
        assert "session.create" in caps

    def test_openwebui_connector_capabilities(self):
        from aios.integrations.oss.openwebui import OpenWebUIIntegration
        from aios.integrations.oss.connectors import OpenWebUIConnector
        integ = OpenWebUIIntegration(make_config("openwebui"))
        conn = OpenWebUIConnector(integ)
        caps = conn.capabilities()
        assert "model.list" in caps
        assert "inference.run" in caps
        assert "pipeline.list" in caps

    def test_continue_connector_capabilities(self):
        from aios.integrations.oss.continue_dev import ContinueIntegration
        from aios.integrations.oss.connectors import ContinueConnector
        integ = ContinueIntegration(make_config("continue"))
        conn = ContinueConnector(integ)
        caps = conn.capabilities()
        assert "ide.index" in caps
        assert "ide.autocomplete" in caps
        assert "ide.run_mcp" in caps

    def test_jan_connector_capabilities(self):
        from aios.integrations.oss.jan import JanIntegration
        from aios.integrations.oss.connectors import JanConnector
        integ = JanIntegration(make_config("jan"))
        conn = JanConnector(integ)
        caps = conn.capabilities()
        assert "model.download" in caps
        assert "model.start" in caps
        assert "engine.list" in caps


# ─── Factory Functions ───────────────────────────────────────────────────────

class TestOSSFactories:
    def test_create_oss_integration(self):
        from aios.integrations.oss import create_oss_integration, ADAPTER_REGISTRY
        for name in ADAPTER_REGISTRY:
            integ = create_oss_integration(name, make_config(name))
            assert integ.name == name or integ.name == ""

    def test_create_oss_connector(self):
        from aios.integrations.oss import create_oss_connector, create_oss_integration, ADAPTER_REGISTRY
        for name in ADAPTER_REGISTRY:
            integ = create_oss_integration(name, make_config(name))
            conn = create_oss_connector(name, integ)
            assert len(conn.bindings()) > 0

    def test_create_oss_unknown_raises(self):
        from aios.integrations.oss import create_oss_integration
        with pytest.raises(ValueError, match="Unknown OSS adapter"):
            create_oss_integration("nonexistent")

    def test_adapter_registry_has_all(self):
        from aios.integrations.oss import ADAPTER_REGISTRY
        expected = {
            "openjarvis", "openhands", "openinterpreter", "anythingllm",
            "librechat", "openwebui", "continue", "jan",
        }
        assert set(ADAPTER_REGISTRY.keys()) == expected

    def test_upstream_versions_populated(self):
        from aios.integrations.oss import UPSTREAM_VERSIONS
        assert len(UPSTREAM_VERSIONS) == 8

    def test_upstream_licenses_populated(self):
        from aios.integrations.oss import UPSTREAM_LICENSES
        assert len(UPSTREAM_LICENSES) == 8
        assert UPSTREAM_LICENSES["openjarvis"] == "MIT"
        assert UPSTREAM_LICENSES["continue"] == "Apache-2.0"
        assert UPSTREAM_LICENSES["jan"] == "AGPL-3.0"


# ─── Registry Integration ───────────────────────────────────────────────────

class TestOSSRegistryIntegration:
    def test_register_all_oss(self):
        from aios.integrations.oss import register_all_oss
        from aios.integrations.registry import IntegrationRegistry
        from aios.integrations.connector import ConnectorRegistry

        int_reg = IntegrationRegistry()
        conn_reg = ConnectorRegistry()
        results = register_all_oss(int_reg, conn_reg)

        assert len(results) == 8
        assert int_reg.count == 8
        assert conn_reg.count == 8

        for name, info in results.items():
            assert "available" in info
            assert "integration_registered" in info
            assert "connector_registered" in info
            assert info["integration_registered"] is True
            assert info["connector_registered"] is True


# ─── License Preservation ───────────────────────────────────────────────────

class TestLicensePreservation:
    def test_all_upstream_licenses_documented(self):
        from aios.integrations.oss import UPSTREAM_LICENSES, ADAPTER_REGISTRY
        for name in ADAPTER_REGISTRY:
            assert name in UPSTREAM_LICENSES, f"Missing license for {name}"
            assert len(UPSTREAM_LICENSES[name]) > 0, f"Empty license for {name}"

    def test_openwebui_is_bsd(self):
        from aios.integrations.oss import UPSTREAM_LICENSES
        assert UPSTREAM_LICENSES["openwebui"] == "BSD-2-Clause"

    def test_continue_is_apache(self):
        from aios.integrations.oss import UPSTREAM_LICENSES
        assert UPSTREAM_LICENSES["continue"] == "Apache-2.0"

    def test_jan_is_agpl(self):
        from aios.integrations.oss import UPSTREAM_LICENSES
        assert UPSTREAM_LICENSES["jan"] == "AGPL-3.0"
