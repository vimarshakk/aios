"""OSS Connectors — bind AIOS capabilities to upstream OSS integrations.

Each connector declares which capabilities it satisfies and routes invocations
to the backing Integration. Follows the same pattern as built-in connectors
(GitHub, Slack, etc.) but for upstream OSS projects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aios.integrations.connector import Connector, ConnectorBinding

if TYPE_CHECKING:
    from aios.integrations.base import Integration


class OpenJarvisConnector(Connector):
    """Connector for OpenJarvis workflow, scheduling, evaluation, and reasoning."""

    def __init__(self, integration: Integration) -> None:
        super().__init__(integration, name="openjarvis")

    def bindings(self) -> list[ConnectorBinding]:
        return [
            ConnectorBinding(
                capability="workflow.execute",
                action="execute_workflow",
                description="Execute a workflow by name",
            ),
            ConnectorBinding(
                capability="workflow.schedule",
                action="schedule_task",
                description="Schedule a task for deferred execution",
            ),
            ConnectorBinding(
                capability="evaluation.run",
                action="evaluate",
                description="Run an evaluation metric",
            ),
            ConnectorBinding(
                capability="reasoning.invoke",
                action="reason",
                description="Invoke a reasoning utility",
            ),
            ConnectorBinding(
                capability="workflow.list",
                action="list_workflows",
                description="List available workflows",
            ),
            ConnectorBinding(
                capability="evaluation.list",
                action="list_evaluators",
                description="List available evaluators",
            ),
        ]


class OpenHandsConnector(Connector):
    """Connector for OpenHands coding agent with sandbox, git, and browser."""

    def __init__(self, integration: Integration) -> None:
        super().__init__(integration, name="openhands")

    def bindings(self) -> list[ConnectorBinding]:
        return [
            ConnectorBinding(
                capability="coding.sandbox",
                action="run_sandbox",
                description="Execute code in a sandbox",
            ),
            ConnectorBinding(
                capability="coding.git",
                action="git_operation",
                description="Perform git operations",
            ),
            ConnectorBinding(
                capability="coding.edit_repository",
                action="edit_repository",
                description="Autonomously edit a repository",
            ),
            ConnectorBinding(
                capability="coding.browse",
                action="browse_url",
                description="Browser-assisted coding",
            ),
            ConnectorBinding(
                capability="coding.run_task",
                action="run_task",
                description="Execute a full coding task",
            ),
            ConnectorBinding(
                capability="coding.list_sessions",
                action="list_sessions",
                description="List active coding sessions",
            ),
        ]


class OpenInterpreterConnector(Connector):
    """Connector for Open Interpreter desktop agent with shell and Python execution."""

    def __init__(self, integration: Integration) -> None:
        super().__init__(integration, name="openinterpreter")

    def bindings(self) -> list[ConnectorBinding]:
        return [
            ConnectorBinding(
                capability="desktop.shell",
                action="run_shell",
                description="Execute a shell command",
            ),
            ConnectorBinding(
                capability="desktop.python",
                action="run_python",
                description="Execute Python code",
            ),
            ConnectorBinding(
                capability="desktop.automate",
                action="desktop_automate",
                description="Desktop automation",
            ),
            ConnectorBinding(
                capability="desktop.file_read",
                action="file_read",
                description="Read file contents",
            ),
            ConnectorBinding(
                capability="desktop.file_write",
                action="file_write",
                description="Write file contents",
            ),
            ConnectorBinding(
                capability="desktop.file_list",
                action="file_list",
                description="List directory contents",
            ),
            ConnectorBinding(
                capability="desktop.chat",
                action="chat",
                description="Free-form desktop task conversation",
            ),
        ]


class AnythingLLMConnector(Connector):
    """Connector for AnythingLLM document ingestion, RAG, and retrieval."""

    def __init__(self, integration: Integration) -> None:
        super().__init__(integration, name="anythingllm")

    def bindings(self) -> list[ConnectorBinding]:
        return [
            ConnectorBinding(
                capability="rag.ingest",
                action="ingest_document",
                description="Ingest a document into a workspace",
            ),
            ConnectorBinding(
                capability="rag.embed",
                action="embed",
                description="Generate embeddings for text",
            ),
            ConnectorBinding(
                capability="rag.retrieve",
                action="retrieve",
                description="Retrieve relevant documents",
            ),
            ConnectorBinding(
                capability="rag.query",
                action="rag_query",
                description="Full RAG pipeline query",
            ),
            ConnectorBinding(
                capability="rag.list_workspaces",
                action="list_workspaces",
                description="List available workspaces",
            ),
            ConnectorBinding(
                capability="rag.list_documents",
                action="list_documents",
                description="List documents in a workspace",
            ),
            ConnectorBinding(
                capability="rag.delete_document",
                action="delete_document",
                description="Remove a document",
            ),
            ConnectorBinding(
                capability="rag.configure",
                action="configure",
                description="Configure AnythingLLM connection",
            ),
        ]


class LibreChatConnector(Connector):
    """Connector for LibreChat conversations, artifacts, and sessions."""

    def __init__(self, integration: Integration) -> None:
        super().__init__(integration, name="librechat")

    def bindings(self) -> list[ConnectorBinding]:
        return [
            ConnectorBinding(
                capability="conversation.create",
                action="create_conversation",
                description="Create a new conversation",
            ),
            ConnectorBinding(
                capability="conversation.send",
                action="send_message",
                description="Send a message in a conversation",
            ),
            ConnectorBinding(
                capability="conversation.get",
                action="get_conversation",
                description="Retrieve conversation history",
            ),
            ConnectorBinding(
                capability="conversation.list",
                action="list_conversations",
                description="List available conversations",
            ),
            ConnectorBinding(
                capability="conversation.render_markdown",
                action="render_markdown",
                description="Render markdown to HTML",
            ),
            ConnectorBinding(
                capability="artifact.create",
                action="create_artifact",
                description="Create an artifact",
            ),
            ConnectorBinding(
                capability="artifact.get",
                action="get_artifact",
                description="Retrieve an artifact",
            ),
            ConnectorBinding(
                capability="artifact.list",
                action="list_artifacts",
                description="List artifacts in a conversation",
            ),
            ConnectorBinding(
                capability="session.create",
                action="create_session",
                description="Create a new session",
            ),
            ConnectorBinding(
                capability="session.get",
                action="get_session",
                description="Retrieve session details",
            ),
            ConnectorBinding(
                capability="session.end",
                action="end_session",
                description="End a session",
            ),
        ]


class OpenWebUIConnector(Connector):
    """Connector for Open WebUI model management, providers, and inference."""

    def __init__(self, integration: Integration) -> None:
        super().__init__(integration, name="openwebui")

    def bindings(self) -> list[ConnectorBinding]:
        return [
            ConnectorBinding(
                capability="model.list",
                action="list_models",
                description="List available local models",
            ),
            ConnectorBinding(
                capability="model.get",
                action="get_model",
                description="Get model details",
            ),
            ConnectorBinding(
                capability="model.download",
                action="download_model",
                description="Download a model",
            ),
            ConnectorBinding(
                capability="model.delete",
                action="delete_model",
                description="Remove a local model",
            ),
            ConnectorBinding(
                capability="provider.configure",
                action="configure_provider",
                description="Configure an inference provider",
            ),
            ConnectorBinding(
                capability="provider.list",
                action="list_providers",
                description="List configured providers",
            ),
            ConnectorBinding(
                capability="inference.run",
                action="inference",
                description="Run inference through a model",
            ),
            ConnectorBinding(
                capability="pipeline.list",
                action="list_pipelines",
                description="List pipeline components",
            ),
            ConnectorBinding(
                capability="pipeline.get",
                action="get_pipeline",
                description="Get pipeline details",
            ),
        ]


class ContinueConnector(Connector):
    """Connector for Continue IDE agent, codebase indexing, and MCP."""

    def __init__(self, integration: Integration) -> None:
        super().__init__(integration, name="continue")

    def bindings(self) -> list[ConnectorBinding]:
        return [
            ConnectorBinding(
                capability="ide.index",
                action="index_codebase",
                description="Build or update codebase index",
            ),
            ConnectorBinding(
                capability="ide.autocomplete",
                action="autocomplete",
                description="Get autocomplete suggestions",
            ),
            ConnectorBinding(
                capability="ide.chat",
                action="chat",
                description="Free-form code conversation",
            ),
            ConnectorBinding(
                capability="ide.edit_code",
                action="edit_code",
                description="Apply code edits with context",
            ),
            ConnectorBinding(
                capability="ide.get_definitions",
                action="get_definitions",
                description="Look up symbol definitions",
            ),
            ConnectorBinding(
                capability="ide.get_references",
                action="get_references",
                description="Find all references to a symbol",
            ),
            ConnectorBinding(
                capability="ide.run_mcp",
                action="run_mcp",
                description="Execute an MCP tool",
            ),
            ConnectorBinding(
                capability="ide.list_mcp_tools",
                action="list_mcp_tools",
                description="List available MCP tools",
            ),
            ConnectorBinding(
                capability="ide.get_context",
                action="get_context",
                description="Get relevant context for a query",
            ),
        ]


class JanConnector(Connector):
    """Connector for Jan model downloads, lifecycle, and version management."""

    def __init__(self, integration: Integration) -> None:
        super().__init__(integration, name="jan")

    def bindings(self) -> list[ConnectorBinding]:
        return [
            ConnectorBinding(
                capability="model.list",
                action="list_models",
                description="List all installed models",
            ),
            ConnectorBinding(
                capability="model.get",
                action="get_model",
                description="Get model details",
            ),
            ConnectorBinding(
                capability="model.download",
                action="download_model",
                description="Download a model from Jan hub",
            ),
            ConnectorBinding(
                capability="model.delete",
                action="delete_model",
                description="Remove a model from disk",
            ),
            ConnectorBinding(
                capability="model.update",
                action="update_model",
                description="Update a model to latest version",
            ),
            ConnectorBinding(
                capability="model.start",
                action="start_model",
                description="Load a model into memory",
            ),
            ConnectorBinding(
                capability="model.stop",
                action="stop_model",
                description="Unload a model from memory",
            ),
            ConnectorBinding(
                capability="engine.list",
                action="list_engines",
                description="List available inference engines",
            ),
            ConnectorBinding(
                capability="engine.configure",
                action="configure_engine",
                description="Configure engine settings",
            ),
        ]


__all__ = [
    "AnythingLLMConnector",
    "ContinueConnector",
    "JanConnector",
    "LibreChatConnector",
    "OpenHandsConnector",
    "OpenInterpreterConnector",
    "OpenJarvisConnector",
    "OpenWebUIConnector",
]
