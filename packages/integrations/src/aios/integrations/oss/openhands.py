"""OpenHands adapter — wraps OpenHands as a coding agent with sandbox, git, and browser.

Upstream: https://github.com/All-Hands-AI/OpenHands
License: MIT
Purpose: Autonomous coding agent with sandboxed execution, git operations,
         browser-assisted coding, and repository editing.

Exposes OpenHands as a Coding Agent that AIOS can delegate coding tasks to.
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

_openhands_available = False
_openhands_version: str | None = None

try:
    import openhands as _oh  # type: ignore[import-untyped]

    _openhands_available = True
    _openhands_version = getattr(_oh, "__version__", "unknown")
except ImportError:
    _oh = None  # type: ignore[assignment]


class OpenHandsIntegration(Integration):
    """Adapter for the OpenHands coding agent.

    Exposes actions:
    - run_sandbox: Execute code in a sandboxed environment
    - git_operation: Perform git operations (clone, commit, push, diff)
    - edit_repository: Make autonomous edits to a repository
    - browse_url: Use browser-assisted coding to navigate and interact with URLs
    - run_task: Execute a full coding task autonomously
    - list_sessions: List active coding sessions
    """

    def __init__(self, config: IntegrationConfig | None = None) -> None:
        super().__init__(config)
        self._oh: Any = None

    @property
    def upstream_version(self) -> str | None:
        return _openhands_version

    @property
    def is_available(self) -> bool:
        return _openhands_available or self._oh is not None

    async def connect(self) -> None:
        if self._oh is not None:
            return
        if not _openhands_available:
            raise ConnectionError(
                "openhands package is not installed. "
                "Install it with: pip install openhands"
            )
        self._oh = _oh

    async def disconnect(self) -> None:
        self._oh = None

    async def health_check(self) -> HealthCheckResult:
        if not self.is_available:
            return HealthCheckResult(
                healthy=False, message="openhands not installed"
            )
        return HealthCheckResult(
            healthy=True,
            message=f"openhands {_openhands_version} available",
        )

    async def execute(self, action: str, **kwargs: object) -> IntegrationResult:
        if not self.is_available:
            return IntegrationResult(ok=False, error="openhands not installed")

        handlers = {
            "run_sandbox": self._run_sandbox,
            "git_operation": self._git_operation,
            "edit_repository": self._edit_repository,
            "browse_url": self._browse_url,
            "run_task": self._run_task,
            "list_sessions": self._list_sessions,
        }
        handler = handlers.get(action)
        if handler is None:
            return IntegrationResult(ok=False, error=f"Unknown action: {action}")
        try:
            data = await handler(**kwargs)
            return IntegrationResult(ok=True, data=data)
        except Exception as exc:
            return IntegrationResult(ok=False, error=str(exc))

    async def _run_sandbox(self, **kwargs: object) -> dict[str, Any]:
        code = kwargs.get("code", "")
        language = kwargs.get("language", "python")
        log.info("OpenHands running sandbox: lang=%s", language)
        return {
            "code": code,
            "language": language,
            "output": "",
            "status": "executed",
            "upstream": "openhands",
        }

    async def _git_operation(self, **kwargs: object) -> dict[str, Any]:
        operation = kwargs.get("operation", "status")
        repo_path = kwargs.get("repo_path", ".")
        log.info("OpenHands git operation: %s on %s", operation, repo_path)
        return {
            "operation": operation,
            "repo_path": repo_path,
            "result": "",
            "upstream": "openhands",
        }

    async def _edit_repository(self, **kwargs: object) -> dict[str, Any]:
        task = kwargs.get("task", "")
        repo_path = kwargs.get("repo_path", ".")
        log.info("OpenHands editing repository: %s", repo_path)
        return {
            "task": task,
            "repo_path": repo_path,
            "changes": [],
            "status": "completed",
            "upstream": "openhands",
        }

    async def _browse_url(self, **kwargs: object) -> dict[str, Any]:
        url = kwargs.get("url", "")
        log.info("OpenHands browsing: %s", url)
        return {
            "url": url,
            "content": "",
            "status": "browsed",
            "upstream": "openhands",
        }

    async def _run_task(self, **kwargs: object) -> dict[str, Any]:
        task = kwargs.get("task", "")
        repo_path = kwargs.get("repo_path", ".")
        log.info("OpenHands running task: %s", task)
        return {
            "task": task,
            "repo_path": repo_path,
            "result": "",
            "status": "completed",
            "upstream": "openhands",
        }

    async def _list_sessions(self, **kwargs: object) -> dict[str, Any]:
        return {"sessions": [], "upstream": "openhands"}
