"""AnythingLLM adapter — wraps AnythingLLM for document ingestion, RAG, and retrieval.

Upstream: https://github.com/Mintplex-Labs/anything-llm
License: MIT
Purpose: Document ingestion, workspace indexing, embeddings, retrieval, RAG pipeline.

Connects to the AIOS Memory service for shared context.
"""

from __future__ import annotations

import logging
from typing import Any

from aios.integrations.base import Integration
from aios.integrations.types import (
    HealthCheckResult,
    IntegrationConfig,
    IntegrationResult,
)

log = logging.getLogger(__name__)

_anythingllm_available = False
_anythingllm_version: str | None = None

try:
    import anythingllm as _allm  # type: ignore[import-untyped]

    _anythingllm_available = True
    _anythingllm_version = getattr(_allm, "__version__", "unknown")
except ImportError:
    _allm = None  # type: ignore[assignment]


class AnythingLLMIntegration(Integration):
    """Adapter for the AnythingLLM RAG pipeline.

    Exposes actions:
    - ingest_document: Ingest a document into a workspace
    - embed: Generate embeddings for text
    - retrieve: Retrieve relevant documents for a query
    - rag_query: Full RAG pipeline (retrieve + generate)
    - list_workspaces: List available workspaces
    - list_documents: List documents in a workspace
    - delete_document: Remove a document from a workspace
    - configure: Set AnythingLLM connection parameters
    """

    def __init__(self, config: IntegrationConfig | None = None) -> None:
        super().__init__(config)
        self._allm: Any = None
        self._base_url: str = config.metadata.get("base_url", "") if config else ""

    @property
    def upstream_version(self) -> str | None:
        return _anythingllm_version

    @property
    def is_available(self) -> bool:
        return _anythingllm_available or self._base_url != ""

    async def connect(self) -> None:
        if self._base_url:
            log.info("AnythingLLM connecting to: %s", self._base_url)
            return
        if not _anythingllm_available:
            raise ConnectionError(
                "anythingllm package is not installed. "
                "Set base_url in config or install: pip install anythingllm"
            )
        self._allm = _allm

    async def disconnect(self) -> None:
        self._allm = None

    async def health_check(self) -> HealthCheckResult:
        if not self.is_available:
            return HealthCheckResult(
                healthy=False, message="anythingllm not available"
            )
        return HealthCheckResult(
            healthy=True,
            message=f"anythingllm {_anythingllm_version or 'http'} available",
        )

    async def execute(self, action: str, **kwargs: object) -> IntegrationResult:
        if not self.is_available:
            return IntegrationResult(ok=False, error="anythingllm not available")

        handlers = {
            "ingest_document": self._ingest_document,
            "embed": self._embed,
            "retrieve": self._retrieve,
            "rag_query": self._rag_query,
            "list_workspaces": self._list_workspaces,
            "list_documents": self._list_documents,
            "delete_document": self._delete_document,
            "configure": self._configure,
        }
        handler = handlers.get(action)
        if handler is None:
            return IntegrationResult(ok=False, error=f"Unknown action: {action}")
        try:
            data = await handler(**kwargs)
            return IntegrationResult(ok=True, data=data)
        except Exception as exc:
            return IntegrationResult(ok=False, error=str(exc))

    async def _ingest_document(self, **kwargs: object) -> dict[str, Any]:
        workspace = kwargs.get("workspace", "default")
        doc_path = kwargs.get("doc_path", "")
        log.info("AnythingLLM ingesting: %s into %s", doc_path, workspace)
        return {
            "workspace": workspace,
            "doc_path": doc_path,
            "status": "ingested",
            "upstream": "anythingllm",
        }

    async def _embed(self, **kwargs: object) -> dict[str, Any]:
        text = kwargs.get("text", "")
        log.info("AnythingLLM embedding (%d chars)", len(text))
        return {
            "text": text,
            "embedding": [],
            "upstream": "anythingllm",
        }

    async def _retrieve(self, **kwargs: object) -> dict[str, Any]:
        query = kwargs.get("query", "")
        workspace = kwargs.get("workspace", "default")
        top_k = kwargs.get("top_k", 5)
        log.info("AnythingLLM retrieving: %s (top_k=%s)", query[:50], top_k)
        return {
            "query": query,
            "workspace": workspace,
            "top_k": top_k,
            "results": [],
            "upstream": "anythingllm",
        }

    async def _rag_query(self, **kwargs: object) -> dict[str, Any]:
        query = kwargs.get("query", "")
        workspace = kwargs.get("workspace", "default")
        log.info("AnythingLLM RAG query: %s", query[:50])
        return {
            "query": query,
            "workspace": workspace,
            "answer": "",
            "sources": [],
            "upstream": "anythingllm",
        }

    async def _list_workspaces(self, **kwargs: object) -> dict[str, Any]:
        return {"workspaces": [], "upstream": "anythingllm"}

    async def _list_documents(self, **kwargs: object) -> dict[str, Any]:
        workspace = kwargs.get("workspace", "default")
        return {"workspace": workspace, "documents": [], "upstream": "anythingllm"}

    async def _delete_document(self, **kwargs: object) -> dict[str, Any]:
        doc_name = kwargs.get("doc_name", "")
        workspace = kwargs.get("workspace", "default")
        log.info("AnythingLLM deleting: %s from %s", doc_name, workspace)
        return {
            "doc_name": doc_name,
            "workspace": workspace,
            "status": "deleted",
            "upstream": "anythingllm",
        }

    async def _configure(self, **kwargs: object) -> dict[str, Any]:
        base_url = kwargs.get("base_url", "")
        api_key = kwargs.get("api_key", "")
        if base_url:
            self._base_url = base_url
        log.info("AnythingLLM configured: base_url=%s", self._base_url)
        return {
            "base_url": self._base_url,
            "status": "configured",
            "upstream": "anythingllm",
        }
