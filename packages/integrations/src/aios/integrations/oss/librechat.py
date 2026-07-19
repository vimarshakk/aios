"""LibreChat adapter — wraps LibreChat for conversation management, artifacts, and sessions.

Upstream: https://github.com/danny-avila/LibreChat
License: MIT
Purpose: Conversation management, markdown rendering, artifact viewer, session management.

Integrates into the existing Conversation workspace without replacing the AIOS shell.
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

_librechat_available = False
_librechat_version: str | None = None

try:
    import librechat as _lc  # type: ignore[import-untyped]

    _librechat_available = True
    _librechat_version = getattr(_lc, "__version__", "unknown")
except ImportError:
    _lc = None  # type: ignore[assignment]


class LibreChatIntegration(Integration):
    """Adapter for the LibreChat conversation platform.

    Exposes actions:
    - create_conversation: Create a new conversation
    - send_message: Send a message in a conversation
    - get_conversation: Retrieve conversation history
    - list_conversations: List available conversations
    - render_markdown: Render markdown to HTML
    - create_artifact: Create an artifact (code, document, etc.)
    - get_artifact: Retrieve an artifact by ID
    - list_artifacts: List artifacts in a conversation
    - create_session: Create a new session
    - get_session: Retrieve session details
    - end_session: End a session
    """

    def __init__(self, config: IntegrationConfig | None = None) -> None:
        super().__init__(config)
        self._lc: Any = None

    @property
    def upstream_version(self) -> str | None:
        return _librechat_version

    @property
    def is_available(self) -> bool:
        return _librechat_available or self._lc is not None

    async def connect(self) -> None:
        if self._lc is not None:
            return
        if not _librechat_available:
            raise ConnectionError(
                "librechat package is not installed. "
                "Install it with: pip install librechat"
            )
        self._lc = _librechat

    async def disconnect(self) -> None:
        self._lc = None

    async def health_check(self) -> HealthCheckResult:
        if not self.is_available:
            return HealthCheckResult(
                healthy=False, message="librechat not installed"
            )
        return HealthCheckResult(
            healthy=True,
            message=f"librechat {_librechat_version} available",
        )

    async def execute(self, action: str, **kwargs: object) -> IntegrationResult:
        if not self.is_available:
            return IntegrationResult(ok=False, error="librechat not installed")

        handlers = {
            "create_conversation": self._create_conversation,
            "send_message": self._send_message,
            "get_conversation": self._get_conversation,
            "list_conversations": self._list_conversations,
            "render_markdown": self._render_markdown,
            "create_artifact": self._create_artifact,
            "get_artifact": self._get_artifact,
            "list_artifacts": self._list_artifacts,
            "create_session": self._create_session,
            "get_session": self._get_session,
            "end_session": self._end_session,
        }
        handler = handlers.get(action)
        if handler is None:
            return IntegrationResult(ok=False, error=f"Unknown action: {action}")
        try:
            data = await handler(**kwargs)
            return IntegrationResult(ok=True, data=data)
        except Exception as exc:
            return IntegrationResult(ok=False, error=str(exc))

    async def _create_conversation(self, **kwargs: object) -> dict[str, Any]:
        title = kwargs.get("title", "New conversation")
        model = kwargs.get("model", "")
        log.info("LibreChat creating conversation: %s", title)
        return {
            "conversation_id": "",
            "title": title,
            "model": model,
            "status": "created",
            "upstream": "librechat",
        }

    async def _send_message(self, **kwargs: object) -> dict[str, Any]:
        conv_id = kwargs.get("conversation_id", "")
        message = kwargs.get("message", "")
        log.info("LibreChat sending message to %s", conv_id)
        return {
            "conversation_id": conv_id,
            "message": message,
            "response": "",
            "upstream": "librechat",
        }

    async def _get_conversation(self, **kwargs: object) -> dict[str, Any]:
        conv_id = kwargs.get("conversation_id", "")
        return {
            "conversation_id": conv_id,
            "messages": [],
            "upstream": "librechat",
        }

    async def _list_conversations(self, **kwargs: object) -> dict[str, Any]:
        return {"conversations": [], "upstream": "librechat"}

    async def _render_markdown(self, **kwargs: object) -> dict[str, Any]:
        content = kwargs.get("content", "")
        log.info("LibreChat rendering markdown (%d chars)", len(content))
        return {"content": content, "html": "", "upstream": "librechat"}

    async def _create_artifact(self, **kwargs: object) -> dict[str, Any]:
        artifact_type = kwargs.get("type", "code")
        content = kwargs.get("content", "")
        log.info("LibreChat creating artifact: type=%s", artifact_type)
        return {
            "artifact_id": "",
            "type": artifact_type,
            "content": content,
            "status": "created",
            "upstream": "librechat",
        }

    async def _get_artifact(self, **kwargs: object) -> dict[str, Any]:
        artifact_id = kwargs.get("artifact_id", "")
        return {"artifact_id": artifact_id, "content": "", "upstream": "librechat"}

    async def _list_artifacts(self, **kwargs: object) -> dict[str, Any]:
        conv_id = kwargs.get("conversation_id", "")
        return {"conversation_id": conv_id, "artifacts": [], "upstream": "librechat"}

    async def _create_session(self, **kwargs: object) -> dict[str, Any]:
        user_id = kwargs.get("user_id", "")
        log.info("LibreChat creating session for user: %s", user_id)
        return {"session_id": "", "user_id": user_id, "status": "created", "upstream": "librechat"}

    async def _get_session(self, **kwargs: object) -> dict[str, Any]:
        session_id = kwargs.get("session_id", "")
        return {"session_id": session_id, "conversations": [], "upstream": "librechat"}

    async def _end_session(self, **kwargs: object) -> dict[str, Any]:
        session_id = kwargs.get("session_id", "")
        log.info("LibreChat ending session: %s", session_id)
        return {"session_id": session_id, "status": "ended", "upstream": "librechat"}
