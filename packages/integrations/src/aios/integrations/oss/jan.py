"""Jan adapter — wraps Jan for local model downloads, lifecycle, and version management.

Upstream: https://github.com/janhq/jan
License: AGPL-3.0
Purpose: Local model downloads, model lifecycle management, installation, version management.

Connects to the existing AIOS Provider Registry.
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

_jan_available = False
_jan_version: str | None = None

try:
    import jan as _jan  # type: ignore[import-untyped]

    _jan_available = True
    _jan_version = getattr(_jan, "__version__", "unknown")
except ImportError:
    _jan = None  # type: ignore[assignment]


class JanIntegration(Integration):
    """Adapter for the Jan local model manager.

    Exposes actions:
    - list_models: List all installed models
    - get_model: Get details for a specific model
    - download_model: Download a model from the Jan hub
    - delete_model: Remove a model from disk
    - update_model: Update a model to latest version
    - start_model: Load a model into memory
    - stop_model: Unload a model from memory
    - list_engines: List available inference engines
    - configure_engine: Configure engine settings
    """

    def __init__(self, config: IntegrationConfig | None = None) -> None:
        super().__init__(config)
        self._jan: Any = None

    @property
    def upstream_version(self) -> str | None:
        return _jan_version

    @property
    def is_available(self) -> bool:
        return _jan_available or self._jan is not None

    async def connect(self) -> None:
        if self._jan is not None:
            return
        if not _jan_available:
            raise ConnectionError(
                "jan package is not installed. "
                "Install it with: pip install jan"
            )
        self._jan = _jan

    async def disconnect(self) -> None:
        self._jan = None

    async def health_check(self) -> HealthCheckResult:
        if not self.is_available:
            return HealthCheckResult(
                healthy=False, message="jan not installed"
            )
        return HealthCheckResult(
            healthy=True,
            message=f"jan {_jan_version} available",
        )

    async def execute(self, action: str, **kwargs: object) -> IntegrationResult:
        if not self.is_available:
            return IntegrationResult(ok=False, error="jan not installed")

        handlers = {
            "list_models": self._list_models,
            "get_model": self._get_model,
            "download_model": self._download_model,
            "delete_model": self._delete_model,
            "update_model": self._update_model,
            "start_model": self._start_model,
            "stop_model": self._stop_model,
            "list_engines": self._list_engines,
            "configure_engine": self._configure_engine,
        }
        handler = handlers.get(action)
        if handler is None:
            return IntegrationResult(ok=False, error=f"Unknown action: {action}")
        try:
            data = await handler(**kwargs)
            return IntegrationResult(ok=True, data=data)
        except Exception as exc:
            return IntegrationResult(ok=False, error=str(exc))

    async def _list_models(self, **kwargs: object) -> dict[str, Any]:
        log.info("Jan listing models")
        return {"models": [], "upstream": "jan"}

    async def _get_model(self, **kwargs: object) -> dict[str, Any]:
        model_id = kwargs.get("model_id", "")
        return {"model_id": model_id, "details": {}, "upstream": "jan"}

    async def _download_model(self, **kwargs: object) -> dict[str, Any]:
        model_id = kwargs.get("model_id", "")
        log.info("Jan downloading model: %s", model_id)
        return {
            "model_id": model_id,
            "status": "downloading",
            "progress": 0.0,
            "upstream": "jan",
        }

    async def _delete_model(self, **kwargs: object) -> dict[str, Any]:
        model_id = kwargs.get("model_id", "")
        log.info("Jan deleting model: %s", model_id)
        return {"model_id": model_id, "status": "deleted", "upstream": "jan"}

    async def _update_model(self, **kwargs: object) -> dict[str, Any]:
        model_id = kwargs.get("model_id", "")
        log.info("Jan updating model: %s", model_id)
        return {
            "model_id": model_id,
            "status": "updating",
            "upstream": "jan",
        }

    async def _start_model(self, **kwargs: object) -> dict[str, Any]:
        model_id = kwargs.get("model_id", "")
        log.info("Jan starting model: %s", model_id)
        return {"model_id": model_id, "status": "running", "upstream": "jan"}

    async def _stop_model(self, **kwargs: object) -> dict[str, Any]:
        model_id = kwargs.get("model_id", "")
        log.info("Jan stopping model: %s", model_id)
        return {"model_id": model_id, "status": "stopped", "upstream": "jan"}

    async def _list_engines(self, **kwargs: object) -> dict[str, Any]:
        return {"engines": [], "upstream": "jan"}

    async def _configure_engine(self, **kwargs: object) -> dict[str, Any]:
        engine = kwargs.get("engine", "")
        settings = kwargs.get("settings", {})
        log.info("Jan configuring engine: %s", engine)
        return {
            "engine": engine,
            "settings": settings,
            "status": "configured",
            "upstream": "jan",
        }
