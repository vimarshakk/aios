"""Skill planner — pick and order skills to satisfy a requested goal.

The planner maps a natural-language-ish goal or a capability list to a sequence
of registered skills. It performs **capability-based** matching: a goal maps to
required capabilities, and skills are ordered by how many required capabilities
they cover (most-specific first).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aios.skills.manifest import SkillManifest
    from aios.skills.registry import SkillRegistry


@dataclass(frozen=True)
class PlanStep:
    """A single step in a skill plan."""

    index: int
    skill: str
    rationale: str


@dataclass(frozen=True)
class SkillPlan:
    """An ordered plan of skills to execute for a goal."""

    goal: str
    steps: tuple[PlanStep, ...] = ()

    @property
    def skills(self) -> list[str]:
        return [s.skill for s in self.steps]

    @property
    def empty(self) -> bool:
        return len(self.steps) == 0


class SkillPlanner:
    """Plans skill execution sequences from a goal or capability set."""

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def plan_for_capabilities(
        self, capabilities: list[str], goal: str = ""
    ) -> SkillPlan:
        """Order skills that cover the requested capabilities.

        Skills covering the most requested capabilities rank first; ties are
        broken by name for determinism.
        """
        steps: list[PlanStep] = []
        req = set(capabilities)
        ranked: list[tuple[int, str, SkillManifest]] = []
        for skill in self._registry.manifests():
            covered = sum(1 for c in skill.capabilities if c in req)
            if covered > 0:
                ranked.append((covered, skill.name, skill))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        for i, (covered, name, _skill) in enumerate(ranked):
            steps.append(
                PlanStep(
                    index=i,
                    skill=name,
                    rationale=f"covers {covered} requested capability(ies)",
                )
            )
        return SkillPlan(goal=goal, steps=tuple(steps))

    def plan_for_goal(self, goal: str) -> SkillPlan:
        """Best-effort plan by searching skill name/description for the goal."""
        matches = self._registry.find(goal)
        steps = [
            PlanStep(index=i, skill=s.name, rationale="matches goal text")
            for i, s in enumerate(matches)
        ]
        return SkillPlan(goal=goal, steps=tuple(steps))

    def plan(self, goal: str, capabilities: list[str] | None = None) -> SkillPlan:
        """Plan using explicit capabilities if given, else goal text."""
        if capabilities:
            return self.plan_for_capabilities(capabilities, goal=goal)
        return self.plan_for_goal(goal)


__all__ = ["PlanStep", "SkillPlan", "SkillPlanner"]
