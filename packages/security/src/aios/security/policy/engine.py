"""Policy engine — decide approval level for an action before enforcement."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from aios.security.policy.levels import (
    FORBIDDEN_PERMISSIONS,
    SENSITIVE_PERMISSIONS,
    ApprovalLevel,
)
from aios.security.policy.rules import PolicyRule

if TYPE_CHECKING:
    from aios.agents.capability_catalog import CapabilityCatalog


@dataclass(frozen=True)
class ApprovalDecision:
    """The policy verdict for a requested action.

    Attributes:
        level: Required approval level.
        denied: True if the action is forbidden by policy.
        reason: Human-readable explanation.
        matched_rules: Names of rules that contributed to the decision.
    """

    level: ApprovalLevel
    denied: bool = False
    reason: str = ""
    matched_rules: tuple[str, ...] = ()

    @property
    def requires_approval(self) -> bool:
        """Whether the action needs an interactive approval prompt."""
        return self.level in (ApprovalLevel.ASK_ONCE, ApprovalLevel.ASK_ALWAYS)


@dataclass
class PolicyEngine:
    """Computes the approval level required for a capability/permission set.

    The engine merges:

    1. Forbidden permissions        → ``DENY``
    2. Sensitive permissions        → at least ``ASK_ONCE``
    3. Capability scope (from the catalog) → destructive/privileged raise level
    4. Explicit :class:`PolicyRule` overrides (highest priority wins)

    It never grants permissions itself — enforcement remains the job of the
    frozen :class:`aios.agents.permissions.PermissionChecker`.
    """

    catalog: CapabilityCatalog | None = None
    rules: list[PolicyRule] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Sort rules by descending priority so highest wins on lookup.
        self.rules.sort(key=lambda r: -r.priority)

    # -- decision ---------------------------------------------------------

    def evaluate(
        self,
        capabilities: list[str] | None = None,
        permissions: list[str] | None = None,
        manifest_approval: str | None = None,
    ) -> ApprovalDecision:
        """Compute the approval decision for an action.

        Args:
            capabilities: Capability names the action uses.
            permissions: Permission strings the action requires.
            manifest_approval: The skill manifest's declared approval hint
                (e.g. ``ask_once``); used as a floor, not a ceiling.
        """
        capabilities = capabilities or []
        permissions = permissions or []
        matched: list[str] = []
        level = ApprovalLevel.ALLOW
        reason_parts: list[str] = []

        # 1. Forbidden permissions → hard deny.
        forbidden = [p for p in permissions if p in FORBIDDEN_PERMISSIONS]
        if forbidden:
            return ApprovalDecision(
                level=ApprovalLevel.DENY,
                denied=True,
                reason=f"Forbidden permission(s): {', '.join(forbidden)}",
                matched_rules=("forbidden",),
            )

        # 2. Sensitive permissions → at least ASK_ONCE.
        sensitive = [p for p in permissions if p in SENSITIVE_PERMISSIONS]
        if sensitive:
            level = _max_level(level, ApprovalLevel.ASK_ONCE)
            matched.append("sensitive")
            reason_parts.append(
                f"sensitive permissions: {', '.join(sensitive)}"
            )

        # 3. Capability scope from catalog.
        if self.catalog is not None:
            for cap in capabilities:
                node = self.catalog.get(cap)
                cap_level = _scope_to_level(node.scope.value if node else "safe")
                if cap_level != ApprovalLevel.ALLOW:
                    level = _max_level(level, cap_level)
                    matched.append(f"capability:{cap}")
                    reason_parts.append(f"capability scope: {cap}")

        # 4. Explicit rules (highest priority wins outright).
        for rule in self.rules:
            tokens = list(capabilities) + list(permissions)
            if any(rule.applies_to(t) for t in tokens):
                level = _level_from_str(rule.level)
                matched.append(rule.name)
                reason_parts.append(rule.description or rule.name)
                break  # highest priority rule decides

        # 5. Manifest approval hint acts as a floor.
        if manifest_approval:
            level = _max_level(level, _level_from_str(manifest_approval))

        reason = "; ".join(reason_parts) if reason_parts else "no restrictions"
        return ApprovalDecision(
            level=level,
            denied=False,
            reason=reason,
            matched_rules=tuple(matched),
        )

    def add_rule(self, rule: PolicyRule) -> None:
        """Add a rule and re-sort by priority."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: -r.priority)


# -- helpers ----------------------------------------------------------------


def _level_from_str(value: str) -> ApprovalLevel:
    try:
        return ApprovalLevel(value)
    except ValueError:
        return ApprovalLevel.ASK_ONCE


def _scope_to_level(scope: str) -> ApprovalLevel:
    mapping = {
        "safe": ApprovalLevel.ALLOW,
        "interactive": ApprovalLevel.ASK_ONCE,
        "destructive": ApprovalLevel.ASK_ALWAYS,
        "privileged": ApprovalLevel.ASK_ALWAYS,
    }
    return mapping.get(scope, ApprovalLevel.ASK_ONCE)


def _max_level(a: ApprovalLevel, b: ApprovalLevel) -> ApprovalLevel:
    order = [
        ApprovalLevel.ALLOW,
        ApprovalLevel.ASK_ONCE,
        ApprovalLevel.ASK_ALWAYS,
        ApprovalLevel.DENY,
    ]
    return a if order.index(a) >= order.index(b) else b


__all__ = [
    "ApprovalDecision",
    "ApprovalLevel",
    "PolicyEngine",
    "PolicyRule",
]
