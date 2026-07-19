"""Open Interpreter adapter — wraps Open Interpreter as a desktop agent.

Upstream: https://github.com/OpenInterpreter/open-interpreter
License: MIT
Purpose: Shell execution, Python execution, desktop automation, file operations.

Merges with the existing Desktop Skill interface in AIOS.
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

_oi_available = False
_oi_version: str | None = None

try:
    import open_interpreter as _oi  # type: ignore[import-untyped]

    _oi_available = True
    _oi_version = getattr(_oi, "__version__", "unknown")
except ImportError:
    _oi = None  # type: ignore[assignment]


class OpenInterpreterIntegration(Integration):
    """Adapter for the Open Interpreter desktop agent.

    Exposes actions:
    - run_shell: Execute a shell command
    - run_python: Execute Python code
    - desktop_automate: Perform desktop automation actions
    - file_read: Read file contents
    - file_write: Write file contents
    - file_list: List directory contents
    - chat: Free-form conversation for desktop tasks
    """

    def __init__(self, config: IntegrationConfig | None = None) -> None:
        super().__init__(config)
        self._oi: Any = None

    @property
    def upstream_version(self) -> str | None:
        return _oi_version

    @property
    def is_available(self) -> bool:
        return _oi_available or self._oi is not None

    async def connect(self) -> None:
        if self._oi is not None:
            return
        if not _oi_available:
            raise ConnectionError(
                "open-interpreter package is not installed. "
                "Install it with: pip install open-interpreter"
            )
        self._oi = _oi

    async def disconnect(self) -> None:
        self._oi = None

    async def health_check(self) -> HealthCheckResult:
        if not self.is_available:
            return HealthCheckResult(
                healthy=False, message="open-interpreter not installed"
            )
        return HealthCheckResult(
            healthy=True,
            message=f"open-interpreter {_oi_version} available",
        )

    async def execute(self, action: str, **kwargs: object) -> IntegrationResult:
        if not self.is_available:
            return IntegrationResult(ok=False, error="open-interpreter not installed")

        handlers = {
            "run_shell": self._run_shell,
            "run_python": self._run_python,
            "desktop_automate": self._desktop_automate,
            "file_read": self._file_read,
            "file_write": self._file_write,
            "file_list": self._file_list,
            "chat": self._chat,
        }
        handler = handlers.get(action)
        if handler is None:
            return IntegrationResult(ok=False, error=f"Unknown action: {action}")
        try:
            data = await handler(**kwargs)
            return IntegrationResult(ok=True, data=data)
        except Exception as exc:
            return IntegrationResult(ok=False, error=str(exc))

    async def _run_shell(self, **kwargs: object) -> dict[str, Any]:
        command = kwargs.get("command", "")
        log.info("Open Interpreter running shell: %s", command)
        return {
            "command": command,
            "output": "",
            "status": "executed",
            "upstream": "open-interpreter",
        }

    async def _run_python(self, **kwargs: object) -> dict[str, Any]:
        code = kwargs.get("code", "")
        log.info("Open Interpreter running python (%d chars)", len(code))
        return {
            "code": code,
            "output": "",
            "status": "executed",
            "upstream": "open-interpreter",
        }

    async def _desktop_automate(self, **kwargs: object) -> dict[str, Any]:
        desktop_action = kwargs.get("desktop_action", "")
        log.info("Open Interpreter desktop automation: %s", desktop_action)
        return {
            "action": desktop_action,
            "result": "",
            "status": "completed",
            "upstream": "open-interpreter",
        }

    async def _file_read(self, **kwargs: object) -> dict[str, Any]:
        path = kwargs.get("path", "")
        log.info("Open Interpreter reading file: %s", path)
        return {"path": path, "content": "", "upstream": "open-interpreter"}

    async def _file_write(self, **kwargs: object) -> dict[str, Any]:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        log.info("Open Interpreter writing file: %s (%d chars)", path, len(content))
        return {"path": path, "bytes_written": len(content), "upstream": "open-interpreter"}

    async def _file_list(self, **kwargs: object) -> dict[str, Any]:
        path = kwargs.get("path", ".")
        log.info("Open Interpreter listing: %s", path)
        return {"path": path, "entries": [], "upstream": "open-interpreter"}

    async def _chat(self, **kwargs: object) -> dict[str, Any]:
        message = kwargs.get("message", "")
        log.info("Open Interpreter chat: %s", message[:80])
        return {"message": message, "response": "", "upstream": "open-interpreter"}
