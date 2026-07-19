"""Capability resolver — native-first provider selection (ADR-0022).

AIOS must work completely offline with AIOS-native capabilities. External
services (Composio, GitHub API, Notion, Gmail, …) are *optional providers*, not
dependencies. When the Supervisor (or any caller) asks for a logical capability
such as ``notes.write`` or ``email.send``, the resolver returns the best
available provider:

    1. AIOS-native skill (always preferred, no network).
    2. An optional provider that is currently *available* (connected).
    3. Otherwise the native skill if it exists, else the best optional provider
       (marked unavailable so the caller can surface a clear message).

The resolver never invents capability implementations; it only ranks what is
registered. Native skills are registered by the platform bootstrap; optional
providers (Composio connector, MCP servers) register themselves and report
availability via a callable.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from aios.skills.registry import SkillRegistry


class ProviderKind(StrEnum):
    """Where a capability implementation comes from."""

    NATIVE = "native"
    CONNECTOR = "connector"
    MCP = "mcp"


@dataclass
class Resolution:
    """Result of resolving a logical capability to a provider."""

    capability: str
    provider_kind: ProviderKind | None
    provider_id: str | None
    available: bool
    reason: str = ""

    @property
    def resolved(self) -> bool:
        return self.provider_id is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "provider_kind": self.provider_kind.value if self.provider_kind else None,
            "provider_id": self.provider_id,
            "available": self.available,
            "reason": self.reason,
        }


@dataclass
class _Provider:
    capability: str
    provider_id: str
    kind: ProviderKind
    is_available: Callable[[], bool] | None = None

    def available(self) -> bool:
        if self.is_available is None:
            return True
        try:
            return self.is_available()
        except Exception:
            return False


class CapabilityResolver:
    """Rank providers for a logical capability, native-first.

    Registration is additive and idempotent by ``(capability, provider_id)``.
    """

    def __init__(self, skills: SkillRegistry | None = None) -> None:
        self._skills = skills
        self._providers: dict[str, list[_Provider]] = {}

    def bind_skills(self, skills: SkillRegistry) -> None:
        self._skills = skills

    # -------------------------------------------------------------- registration

    def register_native_skill(self, capability: str, skill_name: str) -> None:
        """Register an AIOS-native skill as the preferred provider."""
        self._add(capability, skill_name, ProviderKind.NATIVE)

    def register_provider(
        self,
        capability: str,
        provider_id: str,
        kind: ProviderKind,
        is_available: Callable[[], bool] | None = None,
    ) -> None:
        """Register an optional provider (connector / MCP) for a capability."""
        self._add(capability, provider_id, kind, is_available)

    def _add(
        self,
        capability: str,
        provider_id: str,
        kind: ProviderKind,
        is_available: Callable[[], bool] | None = None,
    ) -> None:
        lst = self._providers.setdefault(capability, [])
        for p in lst:
            if p.provider_id == provider_id:
                p.kind = kind
                p.is_available = is_available
                return
        lst.append(_Provider(capability, provider_id, kind, is_available))

    # ----------------------------------------------------------------- resolution

    def resolve(self, capability: str) -> Resolution:
        """Return the best provider for ``capability``.

        Native skills are preferred and treated as always available (they need
        no external connection). Optional providers are only used when no
        native skill exists and the provider reports available.
        """
        providers = self._providers.get(capability, [])

        natives = [
            p
            for p in providers
            if p.kind == ProviderKind.NATIVE and self._skill_exists(p.provider_id)
        ]
        if natives:
            native = natives[0]
            return Resolution(
                capability=capability,
                provider_kind=ProviderKind.NATIVE,
                provider_id=native.provider_id,
                available=True,
                reason="AIOS-native skill (offline-capable).",
            )

        # No native; consider optional providers that are currently available.
        opts = [p for p in providers if p.kind != ProviderKind.NATIVE and p.available()]
        if opts:
            opt = opts[0]
            return Resolution(
                capability=capability,
                provider_kind=opt.kind,
                provider_id=opt.provider_id,
                available=True,
                reason=f"Optional {opt.kind.value} provider available.",
            )

        if providers:
            # Something is registered but nothing is available right now.
            first = providers[0]
            return Resolution(
                capability=capability,
                provider_kind=first.kind,
                provider_id=first.provider_id,
                available=False,
                reason="Provider registered but not currently available "
                "(connect the integration to enable).",
            )

        return Resolution(
            capability=capability,
            provider_kind=None,
            provider_id=None,
            available=False,
            reason="No provider registered for this capability.",
        )

    def _skill_exists(self, skill_name: str) -> bool:
        if self._skills is None:
            return True  # trust registration; availability checked at exec time
        return self._skills.has(skill_name)

    def providers_for(self, capability: str) -> list[dict[str, Any]]:
        return [
            {
                "provider_id": p.provider_id,
                "kind": p.kind.value,
                "available": p.available(),
            }
            for p in self._providers.get(capability, [])
        ]

    def capabilities(self) -> list[str]:
        return sorted(self._providers.keys())


__all__ = [
    "CapabilityResolver",
    "ProviderKind",
    "Resolution",
]
