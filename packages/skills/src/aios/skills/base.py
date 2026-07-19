"""Skill base types — the runtime contract for a skill."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aios.skills.manifest import SkillManifest


class SkillStatus(Enum):
    """Outcome status of a skill execution."""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    RUNNING = "running"


@dataclass
class SkillContext:
    """Runtime context passed to a skill when executed.

    Attributes:
        skill_name: Name of the skill being executed.
        inputs: Input parameters from the caller.
        capabilities: Resolved capability nodes available to this skill.
        permissions: Granted frozen permission names.
        state: Mutable scratch space shared across skill steps.
        metadata: Arbitrary caller-provided metadata.
    """

    skill_name: str
    inputs: dict[str, Any] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    """Result of a skill execution.

    Attributes:
        status: Execution outcome.
        outputs: Produced artifacts/values keyed by name.
        error: Error message if failed.
        steps: Ordered log of sub-steps performed.
        data: Arbitrary structured payload.
    """

    status: SkillStatus = SkillStatus.SUCCESS
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    steps: list[str] = field(default_factory=list)
    data: Any = None

    @property
    def ok(self) -> bool:
        """Whether the skill succeeded (success or partial)."""
        return self.status in (SkillStatus.SUCCESS, SkillStatus.PARTIAL)


class Skill(ABC):
    """Abstract base class for skills.

    Subclasses implement :meth:`run` and declare their manifest (either by
    overriding :meth:`manifest` or by passing one at construction time).

    Usage::

        class CodeReviewSkill(Skill):
            async def run(self, ctx: SkillContext) -> SkillResult:
                # use ctx.capabilities, ctx.permissions
                ...
    """

    def __init__(self, manifest: SkillManifest | None = None) -> None:
        self._manifest = manifest

    @property
    def manifest(self) -> SkillManifest:
        """The skill's manifest. Must be set or overridden."""
        if self._manifest is None:
            raise RuntimeError(
                f"Skill '{self.__class__.__name__}' has no manifest. "
                "Pass one to the constructor or override `manifest`."
            )
        return self._manifest

    @property
    def name(self) -> str:
        """Skill name from manifest."""
        return self.manifest.name

    @abstractmethod
    async def run(self, ctx: SkillContext) -> SkillResult:
        """Execute the skill. Implement in subclasses."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
