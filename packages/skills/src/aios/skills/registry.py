"""Skill registry — discovery and lookup of skills by name."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aios.skills.base import Skill
    from aios.skills.manifest import SkillManifest


@dataclass(frozen=True)
class RegistryStats:
    """Snapshot of registry state."""

    total: int = 0
    by_tag: dict[str, int] = field(default_factory=dict)


class SkillRegistry:
    """Registry of skill instances and manifests.

    Usage::

        registry = SkillRegistry()
        registry.register(CodeReviewSkill(manifest))
        skill = registry.get("code-review")
        skills = registry.by_capability("filesystem.write")
    """

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """Register a skill instance. Raises if name already registered."""
        name = skill.name
        if name in self._skills:
            raise ValueError(f"Skill '{name}' already registered")
        self._skills[name] = skill

    def unregister(self, name: str) -> Skill | None:
        """Remove and return a skill by name. Returns None if absent."""
        return self._skills.pop(name, None)

    def get(self, name: str) -> Skill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def has(self, name: str) -> bool:
        """Whether a skill is registered."""
        return name in self._skills

    @property
    def names(self) -> list[str]:
        """Registered skill names."""
        return list(self._skills.keys())

    @property
    def count(self) -> int:
        """Number of registered skills."""
        return len(self._skills)

    def manifests(self) -> list[SkillManifest]:
        """Return manifests of all registered skills."""
        return [s.manifest for s in self._skills.values()]

    def by_capability(self, capability: str) -> list[Skill]:
        """Return skills that require a given capability."""
        return [
            s for s in self._skills.values()
            if s.manifest.requires_capability(capability)
        ]

    def by_permission(self, permission: str) -> list[Skill]:
        """Return skills that require a given frozen permission."""
        return [
            s for s in self._skills.values()
            if s.manifest.requires_permission(permission)
        ]

    def by_tag(self, tag: str) -> list[Skill]:
        """Return skills carrying a given tag."""
        return [s for s in self._skills.values() if tag in s.manifest.tags]

    def find(self, query: str) -> list[Skill]:
        """Case-insensitive substring search over name + description."""
        q = query.lower()
        return [
            s for s in self._skills.values()
            if q in s.name.lower() or q in s.manifest.description.lower()
        ]

    def stats(self) -> RegistryStats:
        """Current registry statistics."""
        tag_counts: dict[str, int] = {}
        for s in self._skills.values():
            for t in s.manifest.tags:
                tag_counts[t] = tag_counts.get(t, 0) + 1
        return RegistryStats(total=len(self._skills), by_tag=tag_counts)

    def clear(self) -> int:
        """Remove all skills. Returns count removed."""
        count = len(self._skills)
        self._skills.clear()
        return count

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    def __len__(self) -> int:
        return len(self._skills)

    def __repr__(self) -> str:
        return f"<SkillRegistry count={len(self._skills)}>"
