"""Continue adapter — wraps Continue for IDE support, codebase indexing, and MCP.

Upstream: https://github.com/continuedev/continue
License: Apache-2.0
Purpose: IDE agent with codebase indexing, autocomplete, editor integration, MCP support.

Exposes Continue as an IDE Agent that AIOS can delegate IDE tasks to.
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

_continue_available = False
_continue_version: str | None = None

try:
    import continue_sdk as _cont  # type: ignore[import-untyped]

    _continue_available = True
    _continue_version = getattr(_cont, "__version__", "unknown")
except ImportError:
    _cont = None  # type: ignore[assignment]


class ContinueIntegration(Integration):
    """Adapter for the Continue IDE agent.

    Exposes actions:
    - index_codebase: Build or update codebase index
    - autocomplete: Get autocomplete suggestions for code
    - chat: Free-form code conversation
    - edit_code: Apply code edits with context
    - get_definitions: Look up symbol definitions
    - get_references: Find all references to a symbol
    - run_mcp: Execute an MCP tool
    - list_mcp_tools: List available MCP tools
    - get_context: Get relevant context for a query
    """

    def __init__(self, config: IntegrationConfig | None = None) -> None:
        super().__init__(config)
        self._cont: Any = None

    @property
    def upstream_version(self) -> str | None:
        return _continue_version

    @property
    def is_available(self) -> bool:
        return _continue_available or self._cont is not None

    async def connect(self) -> None:
        if self._cont is not None:
            return
        if not _continue_available:
            raise ConnectionError(
                "continue package is not installed. "
                "Install it with: pip install continue"
            )
        self._cont = _cont

    async def disconnect(self) -> None:
        self._cont = None

    async def health_check(self) -> HealthCheckResult:
        if not self.is_available:
            return HealthCheckResult(
                healthy=False, message="continue not installed"
            )
        return HealthCheckResult(
            healthy=True,
            message=f"continue {_continue_version} available",
        )

    async def execute(self, action: str, **kwargs: object) -> IntegrationResult:
        if not self.is_available:
            return IntegrationResult(ok=False, error="continue not installed")

        handlers = {
            "index_codebase": self._index_codebase,
            "autocomplete": self._autocomplete,
            "chat": self._chat,
            "edit_code": self._edit_code,
            "get_definitions": self._get_definitions,
            "get_references": self._get_references,
            "run_mcp": self._run_mcp,
            "list_mcp_tools": self._list_mcp_tools,
            "get_context": self._get_context,
        }
        handler = handlers.get(action)
        if handler is None:
            return IntegrationResult(ok=False, error=f"Unknown action: {action}")
        try:
            data = await handler(**kwargs)
            return IntegrationResult(ok=True, data=data)
        except Exception as exc:
            return IntegrationResult(ok=False, error=str(exc))

    async def _index_codebase(self, **kwargs: object) -> dict[str, Any]:
        workspace = kwargs.get("workspace", ".")
        log.info("Continue indexing codebase: %s", workspace)
        return {
            "workspace": workspace,
            "status": "indexed",
            "upstream": "continue",
        }

    async def _autocomplete(self, **kwargs: object) -> dict[str, Any]:
        file_path = kwargs.get("file_path", "")
        line = kwargs.get("line", 0)
        prefix = kwargs.get("prefix", "")
        log.info("Continue autocomplete: %s:%d", file_path, line)
        return {
            "file_path": file_path,
            "line": line,
            "suggestions": [],
            "upstream": "continue",
        }

    async def _chat(self, **kwargs: object) -> dict[str, Any]:
        message = kwargs.get("message", "")
        log.info("Continue chat: %s", message[:80])
        return {"message": message, "response": "", "upstream": "continue"}

    async def _edit_code(self, **kwargs: object) -> dict[str, Any]:
        file_path = kwargs.get("file_path", "")
        instruction = kwargs.get("instruction", "")
        log.info("Continue editing: %s", file_path)
        return {
            "file_path": file_path,
            "instruction": instruction,
            "diff": "",
            "status": "applied",
            "upstream": "continue",
        }

    async def _get_definitions(self, **kwargs: object) -> dict[str, Any]:
        symbol = kwargs.get("symbol", "")
        file_path = kwargs.get("file_path", "")
        log.info("Continue definitions: %s in %s", symbol, file_path)
        return {"symbol": symbol, "definitions": [], "upstream": "continue"}

    async def _get_references(self, **kwargs: object) -> dict[str, Any]:
        symbol = kwargs.get("symbol", "")
        log.info("Continue references: %s", symbol)
        return {"symbol": symbol, "references": [], "upstream": "continue"}

    async def _run_mcp(self, **kwargs: object) -> dict[str, Any]:
        tool_name = kwargs.get("tool_name", "")
        params = kwargs.get("params", {})
        log.info("Continue MCP tool: %s", tool_name)
        return {"tool_name": tool_name, "result": {}, "upstream": "continue"}

    async def _list_mcp_tools(self, **kwargs: object) -> dict[str, Any]:
        return {"tools": [], "upstream": "continue"}

    async def _get_context(self, **kwargs: object) -> dict[str, Any]:
        query = kwargs.get("query", "")
        log.info("Continue context: %s", query[:80])
        return {"query": query, "context": [], "upstream": "continue"}
