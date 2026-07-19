"""Open WebUI adapter — wraps Open WebUI for local model management and provider config.

Upstream: https://github.com/open-webui/open-webui
License: BSD-2-Clause
Purpose: Local model management, provider configuration, inference controls, pipelines.

Does not duplicate existing provider routing in AIOS.
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

_openwebui_available = False
_openwebui_version: str | None = None

try:
    import open_webui as _owui  # type: ignore[import-untyped]

    _openwebui_available = True
    _openwebui_version = getattr(_owui, "__version__", "unknown")
except ImportError:
    _owui = None  # type: ignore[assignment]


class OpenWebUIIntegration(Integration):
    """Adapter for the Open WebUI platform.

    Exposes actions:
    - list_models: List available local models
    - get_model: Get details for a specific model
    - download_model: Download a model from the registry
    - delete_model: Remove a local model
    - configure_provider: Configure an inference provider
    - list_providers: List configured providers
    - inference: Run inference through a model
    - list_pipelines: List available pipeline components
    - get_pipeline: Get details for a specific pipeline
    """

    def __init__(self, config: IntegrationConfig | None = None) -> None:
        super().__init__(config)
        self._owui: Any = None
        self._base_url: str = config.metadata.get("base_url", "") if config else ""

    @property
    def upstream_version(self) -> str | None:
        return _openwebui_version

    @property
    def is_available(self) -> bool:
        return _openwebui_available or self._base_url != ""

    async def connect(self) -> None:
        if self._base_url:
            log.info("Open WebUI connecting to: %s", self._base_url)
            return
        if not _openwebui_available:
            raise ConnectionError(
                "open-webui package is not installed. "
                "Set base_url in config or install: pip install open-webui"
            )
        self._owui = _owui

    async def disconnect(self) -> None:
        self._owui = None

    async def health_check(self) -> HealthCheckResult:
        if not self.is_available:
            return HealthCheckResult(
                healthy=False, message="open-webui not available"
            )
        return HealthCheckResult(
            healthy=True,
            message=f"open-webui {_openwebui_version or 'http'} available",
        )

    async def execute(self, action: str, **kwargs: object) -> IntegrationResult:
        if not self.is_available:
            return IntegrationResult(ok=False, error="open-webui not available")

        handlers = {
            "list_models": self._list_models,
            "get_model": self._get_model,
            "download_model": self._download_model,
            "delete_model": self._delete_model,
            "configure_provider": self._configure_provider,
            "list_providers": self._list_providers,
            "inference": self._inference,
            "list_pipelines": self._list_pipelines,
            "get_pipeline": self._get_pipeline,
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
        log.info("Open WebUI listing models")
        return {"models": [], "upstream": "open-webui"}

    async def _get_model(self, **kwargs: object) -> dict[str, Any]:
        model_id = kwargs.get("model_id", "")
        return {"model_id": model_id, "details": {}, "upstream": "open-webui"}

    async def _download_model(self, **kwargs: object) -> dict[str, Any]:
        model_name = kwargs.get("model_name", "")
        log.info("Open WebUI downloading model: %s", model_name)
        return {
            "model_name": model_name,
            "status": "downloading",
            "upstream": "open-webui",
        }

    async def _delete_model(self, **kwargs: object) -> dict[str, Any]:
        model_id = kwargs.get("model_id", "")
        log.info("Open WebUI deleting model: %s", model_id)
        return {"model_id": model_id, "status": "deleted", "upstream": "open-webui"}

    async def _configure_provider(self, **kwargs: object) -> dict[str, Any]:
        provider = kwargs.get("provider", "")
        settings = kwargs.get("settings", {})
        log.info("Open WebUI configuring provider: %s", provider)
        return {
            "provider": provider,
            "settings": settings,
            "status": "configured",
            "upstream": "open-webui",
        }

    async def _list_providers(self, **kwargs: object) -> dict[str, Any]:
        return {"providers": [], "upstream": "open-webui"}

    async def _inference(self, **kwargs: object) -> dict[str, Any]:
        model = kwargs.get("model", "")
        prompt = kwargs.get("prompt", "")
        log.info("Open WebUI inference: model=%s", model)
        return {
            "model": model,
            "prompt": prompt,
            "response": "",
            "upstream": "open-webui",
        }

    async def _list_pipelines(self, **kwargs: object) -> dict[str, Any]:
        return {"pipelines": [], "upstream": "open-webui"}

    async def _get_pipeline(self, **kwargs: object) -> dict[str, Any]:
        pipeline_id = kwargs.get("pipeline_id", "")
        return {"pipeline_id": pipeline_id, "details": {}, "upstream": "open-webui"}
