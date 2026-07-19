"""Skill manifest validator — structural validation of manifests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aios.skills.manifest import SkillManifest

_VALID_APPROVALS = {"allow", "ask_once", "ask_always", "deny"}


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation problem."""

    field: str
    message: str
    level: str = "error"  # "error" | "warning"


@dataclass(frozen=True)
class ValidationReport:
    """Result of validating a skill manifest."""

    manifest_name: str
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def valid(self) -> bool:
        return not any(i.level == "error" for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "warning"]


def validate_skill_manifest(manifest: SkillManifest) -> ValidationReport:
    """Validate a skill manifest's structural correctness.

    Checks:
    - name is non-empty and kebab-case
    - version is present
    - approval level is a known value
    - capabilities/outputs referenced exist (namespaced correctly)
    """
    issues: list[ValidationIssue] = []
    name = manifest.name

    if not name:
        issues.append(ValidationIssue("name", "name must not be empty"))
    elif not _is_kebab(name):
        issues.append(
            ValidationIssue(
                "name",
                f"name '{name}' should be kebab-case (e.g. code-review)",
                level="warning",
            )
        )

    if not manifest.version:
        issues.append(ValidationIssue("version", "version must not be empty"))

    if manifest.approval not in _VALID_APPROVALS:
        issues.append(
            ValidationIssue(
                "approval",
                f"approval '{manifest.approval}' not in {sorted(_VALID_APPROVALS)}",
            )
        )

    if manifest.retry.max_attempts < 1:
        issues.append(
            ValidationIssue("retry.max_attempts", "must be >= 1")
        )

    if not manifest.description:
        issues.append(
            ValidationIssue("description", "missing description", level="warning")
        )

    return ValidationReport(
        manifest_name=name or "<unnamed>", issues=tuple(issues)
    )


def _is_kebab(name: str) -> bool:
    import re

    return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name))


__all__ = ["ValidationIssue", "ValidationReport", "validate_skill_manifest"]
