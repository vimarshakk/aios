"""Skill manifest — declarative metadata for a skill.

A manifest describes what a skill needs and does, without code. Skills can be
loaded from YAML manifests (see :func:`aios.skills.loader.load_skill`) or
defined inline in code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SkillRetryPolicy:
    """Retry configuration for a skill execution.

    Attributes:
        max_attempts: Maximum number of execution attempts.
        backoff_seconds: Base delay between attempts.
        non_retryable: Error substrings that should not trigger a retry.
    """

    max_attempts: int = 1
    backoff_seconds: float = 1.0
    non_retryable: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillManifest:
    """Declarative description of a skill.

    Attributes:
        name: Unique skill identifier (e.g. ``code-review``).
        version: Semver string.
        description: Human-readable summary.
        inputs: Names of required/optional input parameters.
        outputs: Names of produced outputs.
        capabilities: Capability names this skill requires (catalog keys).
        permissions: Frozen permission names this skill needs.
        prompts: Named prompt templates the skill uses.
        retry: Retry policy for execution.
        approval: Approval level required before execution (see policy engine).
        tags: Freeform tags.
        metadata: Arbitrary extra metadata.
    """

    name: str
    version: str = "1.0.0"
    description: str = ""
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    prompts: tuple[str, ...] = ()
    retry: SkillRetryPolicy = field(default_factory=SkillRetryPolicy)
    approval: str = "ask_once"
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def requires_capability(self, capability: str) -> bool:
        """Whether this skill requires a given capability name."""
        return capability in self.capabilities

    def requires_permission(self, permission: str) -> bool:
        """Whether this skill requires a given frozen permission name."""
        return permission in self.permissions
