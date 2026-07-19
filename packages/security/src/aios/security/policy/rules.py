"""Policy rules — declarative, composable approval rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyRule:
    """A single declarative policy rule.

    Attributes:
        name: Rule identifier.
        matches: Capability or permission names this rule applies to.
        level: Approval level enforced by this rule.
        priority: Higher priority wins on conflict.
        description: Human-readable rationale.
    """

    name: str
    matches: tuple[str, ...] = ()
    level: str = "ask_once"
    priority: int = 0
    description: str = ""

    def applies_to(self, token: str) -> bool:
        """Whether this rule matches a capability or permission name."""
        return token in self.matches
