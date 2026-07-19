"""Built-in AIOS skills.

These are reference implementations demonstrating the skill contract. They are
registered lazily via :func:`register_builtins` so consumers can opt in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aios.skills.base import Skill, SkillContext, SkillResult, SkillStatus
from aios.skills.manifest import SkillManifest

if TYPE_CHECKING:
    from aios.skills.registry import SkillRegistry


class _CodeReviewSkill(Skill):
    """Reference skill: review a code diff using filesystem + terminal caps."""

    def __init__(self) -> None:
        super().__init__(
            SkillManifest(
                name="code-review",
                version="1.0.0",
                description="Review a code diff for quality and risk",
                inputs=("diff", "path"),
                outputs=("findings", "summary"),
                capabilities=("filesystem.read", "terminal.exec"),
                permissions=("FILESYSTEM_READ", "PROCESS_EXEC"),
                approval="ask_once",
                tags=("dev", "quality"),
            )
        )

    async def run(self, ctx: SkillContext) -> SkillResult:
        diff = ctx.inputs.get("diff")
        if not diff:
            return SkillResult(
                status=SkillStatus.FAILED, error="missing 'diff' input",
                steps=["validate inputs"],
            )
        return SkillResult(
            status=SkillStatus.SUCCESS,
            outputs={"findings": [], "summary": "no issues found"},
            steps=["read diff", "analyzed"],
            data={"reviewed": True},
        )


class _WebResearchSkill(Skill):
    """Reference skill: research a topic using network + browser caps."""

    def __init__(self) -> None:
        super().__init__(
            SkillManifest(
                name="web-research",
                version="1.0.0",
                description="Research a topic across the web",
                inputs=("query",),
                outputs=("sources", "summary"),
                capabilities=("browser.navigate", "network.http"),
                permissions=("NETWORK_HTTP",),
                approval="ask_once",
                tags=("research", "web"),
            )
        )

    async def run(self, ctx: SkillContext) -> SkillResult:
        query = ctx.inputs.get("query")
        if not query:
            return SkillResult(
                status=SkillStatus.FAILED, error="missing 'query' input",
                steps=["validate inputs"],
            )
        return SkillResult(
            status=SkillStatus.SUCCESS,
            outputs={"sources": [], "summary": f"research on {query}"},
            steps=["searched", "summarized"],
        )


def register_builtins(registry: SkillRegistry) -> None:
    """Register all built-in skills into the given registry."""
    for skill_cls in (_CodeReviewSkill, _WebResearchSkill):
        registry.register(skill_cls())


__all__ = ["_CodeReviewSkill", "_WebResearchSkill", "register_builtins"]
