"""Skill executor — runs a skill with capability/permission checks and retries."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aios.agents.capability_catalog import CapabilityCatalog
from aios.skills.base import (
    Skill,
    SkillContext,
    SkillResult,
    SkillStatus,
)

if TYPE_CHECKING:
    from aios.skills.manifest import SkillManifest


@dataclass
class ExecutionRecord:
    """Record of a single skill execution attempt."""

    skill: str
    status: SkillStatus
    attempts: int
    duration_ms: float
    error: str | None = None
    outputs: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in (SkillStatus.SUCCESS, SkillStatus.PARTIAL)


class SkillExecutor:
    """Executes skills with validation, permission gating, and retry.

    The executor does NOT decide permissions — it receives an
    :class:`~aios.agents.permissions.PermissionSet` (or list of granted
    permission names) that has already been approved by the permission layer.
    It only verifies the skill's declared requirements are satisfied.
    """

    def __init__(
        self,
        catalog: CapabilityCatalog | None = None,
        granted_permissions: list[str] | None = None,
    ) -> None:
        self._catalog = catalog or CapabilityCatalog()
        self._granted = set(granted_permissions or [])
        self._history: list[ExecutionRecord] = []

    @property
    def history(self) -> list[ExecutionRecord]:
        """Execution history (most recent last)."""
        return list(self._history)

    def check(self, manifest: SkillManifest) -> list[str]:
        """Return list of unsatisfied permission names (empty if all ok)."""
        return [
            perm for perm in manifest.permissions
            if perm not in self._granted
        ]

    async def execute(
        self,
        skill: Skill,
        inputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SkillResult:
        """Execute a skill, validating requirements and applying retry."""
        manifest = skill.manifest
        missing = self.check(manifest)
        if missing:
            result = SkillResult(
                status=SkillStatus.FAILED,
                error=f"Missing permissions: {', '.join(missing)}",
                steps=["permission check failed"],
            )
            self._history.append(
                ExecutionRecord(
                    skill=skill.name, status=result.status,
                    attempts=0, duration_ms=0.0, error=result.error,
                )
            )
            return result

        # Resolve capabilities declared by the skill.
        capabilities = [
            c for c in manifest.capabilities if self._catalog.has(c)
        ]

        ctx = SkillContext(
            skill_name=skill.name,
            inputs=inputs or {},
            capabilities=capabilities,
            permissions=list(manifest.permissions),
            metadata=metadata or {},
        )

        policy = manifest.retry
        attempts = 0
        last: SkillResult | None = None
        start = time.monotonic()
        while attempts < max(policy.max_attempts, 1):
            attempts += 1
            try:
                last = await skill.run(ctx)
                if last.ok or not self._should_retry(last, policy):
                    break
            except Exception as exc:
                last = SkillResult(
                    status=SkillStatus.FAILED,
                    error=f"{type(exc).__name__}: {exc}",
                    steps=[f"exception: {exc}"],
                )
                if not self._should_retry(last, policy):
                    break
        duration_ms = (time.monotonic() - start) * 1000.0
        assert last is not None
        self._history.append(
            ExecutionRecord(
                skill=skill.name, status=last.status, attempts=attempts,
                duration_ms=duration_ms, error=last.error,
                outputs=dict(last.outputs),
            )
        )
        return last

    @staticmethod
    def _should_retry(result: SkillResult, policy) -> bool:
        if result.status == SkillStatus.SUCCESS:
            return False
        if result.error:
            for nr in policy.non_retryable:
                if nr and nr in result.error:
                    return False
        return True

    def reset(self) -> None:
        """Clear execution history."""
        self._history.clear()


__all__ = ["ExecutionRecord", "SkillExecutor"]
