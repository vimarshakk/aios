"""Composio connector — consume the Composio integration ecosystem.

AIOS owns orchestration, memory, permissions and autonomy. For SaaS connectors
(Notion, Slack, Gmail, Linear, Google Drive, …) it should *consume* an existing
ecosystem rather than reimplement hundreds of integrations. Composio provides
managed OAuth, tool discovery and remote execution across many apps behind one
authentication flow.

This module adapts Composio into the ADR-0019 connector contract:

    CapabilityCatalog → Connector → Integration → Composio (transport only)

The :class:`ComposioIntegration` is the thin transport that maps an integration
action (a Composio tool slug) onto ``composio.tools.execute``. The
:class:`ComposioConnector` exposes a curated set of capability bindings for the
most common SaaS apps *and* supports discovery-driven, dynamic tool execution.

``composio`` is an optional, heavy dependency. It is imported lazily so the rest
of AIOS imports cleanly without it; the connector raises a clear error when used
without the SDK installed.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aios.agents.permissions import Permission
from aios.integrations.base import Integration
from aios.integrations.connector import Connector, ConnectorBinding
from aios.integrations.types import (
    HealthCheckResult,
    IntegrationConfig,
    IntegrationResult,
    IntegrationStatus,
)

logger = logging.getLogger("aios.integrations.composio")

if TYPE_CHECKING:
    from aios.agents.permissions import PermissionSet


# Curated, catalog-visible bindings. Each maps an AIOS capability to a Composio
# toolkit + the action slug used by ``composio.tools.execute``. Discovery will
# register finer-grained, toolkit-scoped capabilities on top of these.
_CURATED_BINDINGS: tuple[tuple[str, str, str, str], ...] = (
    # (capability, action-slug, toolkit, description)
    ("composio.github", "GITHUB_CREATE_ISSUE", "github", "Create a GitHub issue"),
    ("composio.github", "GITHUB_CREATE_PULL_REQUEST", "github", "Open a GitHub PR"),
    ("composio.github", "GITHUB_GET_ISSUE", "github", "Read a GitHub issue"),
    ("composio.notion", "NOTION_CREATE_PAGE", "notion", "Create a Notion page"),
    ("composio.notion", "NOTION_SEARCH", "notion", "Search Notion"),
    ("composio.gmail", "GMAIL_SEND_EMAIL", "gmail", "Send an email via Gmail"),
    ("composio.gmail", "GMAIL_FETCH_EMAILS", "gmail", "Read Gmail messages"),
    ("composio.slack", "SLACK_SEND_MESSAGE", "slack", "Send a Slack message"),
    ("composio.linear", "LINEAR_CREATE_ISSUE", "linear", "Create a Linear issue"),
)

# Default entity/user id used for Composio connected accounts when none is
# supplied by the caller. Mirrors Composio's "default" user convention.
DEFAULT_ENTITY = "default"

# Common toolkit slugs used for discovery when no explicit allowlist is given.
DEFAULT_TOOLKITS = (
    "github",
    "notion",
    "gmail",
    "slack",
    "linear",
    "googledrive",
    "calendar",
    "docker",
)


def _require_composio() -> type:
    """Import the Composio SDK, raising a clear error if it is missing."""
    try:
        from composio import Composio  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on optional dep
        raise ImportError(
            "The 'composio' SDK is required for ComposioConnector. "
            "Install it with: uv add composio  (or pip install composio)"
        ) from exc
    return Composio


class ComposioIntegration(Integration):
    """Thin transport integration backing a :class:`ComposioConnector`.

    Maps an integration action (a Composio tool slug) onto
    ``Composio.tools.execute``. The SDK is imported lazily; the integration can
    be constructed without the dependency present, but execution requires it.
    """

    def __init__(
        self,
        config: IntegrationConfig | None = None,
        *,
        api_key: str | None = None,
        entity: str = DEFAULT_ENTITY,
    ) -> None:
        super().__init__(config or IntegrationConfig(name="composio"))
        self._api_key = api_key or (config.api_key if config else None)
        self._entity = entity
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            composio = _require_composio()
            self._client = composio(api_key=self._api_key)
        return self._client

    async def connect(self) -> None:
        # Composio is a stateless remote API; connectivity is verified lazily
        # on first execution. Nothing to establish up front.
        self._get_client()

    async def disconnect(self) -> None:
        self._client = None

    async def health_check(self) -> HealthCheckResult:
        import time

        start = time.monotonic()
        try:
            self._get_client()
            return HealthCheckResult(
                healthy=True,
                latency_ms=(time.monotonic() - start) * 1000.0,
                message="Composio client available",
            )
        except Exception as exc:
            return HealthCheckResult(
                healthy=False,
                latency_ms=(time.monotonic() - start) * 1000.0,
                message=str(exc),
            )

    async def execute(self, action: str, **kwargs: object) -> IntegrationResult:
        """Execute a Composio tool by slug.

        Args:
            action: Composio tool/action slug (e.g. ``GITHUB_CREATE_ISSUE``).
            **kwargs: Tool arguments. ``entity_id`` overrides the default user.
        """
        entity = kwargs.pop("entity_id", self._entity) or self._entity
        try:
            client = self._get_client()
            response = client.tools.execute(
                user_id=entity,
                slug=action,
                arguments=kwargs,
            )
        except Exception as exc:
            return IntegrationResult(
                ok=False,
                error=f"Composio execution failed for '{action}': {exc}",
                status=IntegrationStatus.ERROR,
            )
        data = _extract_response_data(response)
        return IntegrationResult(ok=True, data=data, status=IntegrationStatus.CONNECTED)


def _extract_response_data(response: Any) -> dict[str, Any]:
    """Normalize a Composio execution response into a plain dict."""
    if isinstance(response, dict):
        return response
    for attr in ("data", "response"):
        if hasattr(response, attr):
            value = getattr(response, attr)
            if isinstance(value, dict):
                return value
    if hasattr(response, "__dict__"):
        return {"result": repr(response)}
    return {"result": response}


class ComposioConnector(Connector):
    """Connect AIOS capabilities to the Composio ecosystem.

    Exposes curated bindings for common SaaS apps (visible in the capability
    catalog) and supports discovery-driven execution: any Composio tool slug
    can be invoked dynamically via :meth:`invoke` with ``action=<SLUG>``.
    """

    def __init__(self, integration: Integration) -> None:
        super().__init__(integration, name="composio")

    def bindings(self) -> list[ConnectorBinding]:
        return [
            ConnectorBinding(
                capability=capability,
                action=slug,
                required_permissions=(Permission.NETWORK_HTTP,),
                description=description,
            )
            for capability, slug, _toolkit, description in _CURATED_BINDINGS
        ]

    # -- discovery --------------------------------------------------------

    def toolkit_for(self, capability: str) -> str | None:
        """Return the Composio toolkit slug backing a curated capability."""
        for cap, _slug, toolkit, _desc in _CURATED_BINDINGS:
            if cap == capability:
                return toolkit
        return None

    @property
    def curated_toolkits(self) -> list[str]:
        """Toolkit slugs covered by the curated bindings."""
        seen: list[str] = []
        for _cap, _slug, toolkit, _desc in _CURATED_BINDINGS:
            if toolkit not in seen:
                seen.append(toolkit)
        return seen

    async def discover(self, toolkits: list[str] | None = None) -> list[dict[str, Any]]:
        """Discover available Composio tools.

        Returns a list of tool descriptors (``slug``, ``toolkit``, ``name``,
        ``description``) for the requested toolkits (or a sensible default set).
        Requires the ``composio`` SDK and network egress.
        """
        client = self._composio_client()
        requested = toolkits or list(self.curated_toolkits) or list(DEFAULT_TOOLKITS)
        tools: list[dict[str, Any]] = []
        for toolkit in requested:
            try:
                specs = client.tools.get(user_id=self._entity, toolkits=[toolkit])
            except Exception as exc:
                logger.debug("Composio toolkit '%s' unavailable: %s", toolkit, exc)
                continue
            tools.extend(
                {
                    "slug": spec.get("slug") or spec.get("name"),
                    "toolkit": toolkit,
                    "name": spec.get("name"),
                    "description": spec.get("description", ""),
                }
                for spec in _as_list(specs)
            )
        return tools

    def _composio_client(self) -> Any:
        integration = self._integration
        if isinstance(integration, ComposioIntegration):
            return integration._get_client()
        # Fall back to constructing a throwaway client via the SDK.
        return _require_composio()(api_key=None)

    @property
    def _entity(self) -> str:
        integration = self._integration
        if isinstance(integration, ComposioIntegration):
            return integration._entity
        return DEFAULT_ENTITY

    # -- dynamic invocation ---------------------------------------------

    async def invoke(
        self,
        capability: str,
        perms: PermissionSet,
        **params: object,
    ) -> IntegrationResult:
        """Route an invocation to Composio.

        Supports two forms:
        - A curated capability (e.g. ``composio.github``) → mapped slug.
        - A dynamic ``action=<COMPOSIO_SLUG>`` param → executed directly,
          enabling discovery-driven tools not present in :meth:`bindings`.

        All external API calls require ``Permission.NETWORK_HTTP``.
        """
        from aios.integrations.types import IntegrationResult

        if not perms.has_all((Permission.NETWORK_HTTP,)):
            return IntegrationResult(
                ok=False,
                error=f"Missing permission for Composio '{capability}': network.http",
            )

        action = params.pop("action", None)
        if action is None:
            binding = self.binding_for(capability)
            if binding is None:
                return IntegrationResult(
                    ok=False,
                    error=(
                        f"ComposioConnector cannot handle '{capability}'. "
                        f"Pass action=<COMPOSIO_SLUG> for dynamic execution."
                    ),
                )
            action = binding.action

        return await self._integration.safe_execute(action, **params)


def _as_list(value: Any) -> list[dict[str, Any]]:
    """Coerce a Composio tool spec (dict or list) into a list of dicts."""
    if value is None:
        return []
    if isinstance(value, dict):
        for key in ("tools", "actions", "items"):
            if key in value and isinstance(value[key], list):
                return [v for v in value[key] if isinstance(v, dict)]
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    return []


__all__ = [
    "DEFAULT_ENTITY",
    "ComposioConnector",
    "ComposioIntegration",
]
