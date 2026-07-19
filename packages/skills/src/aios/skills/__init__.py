"""AIOS Skills System.

A **skill** is a reusable, composable capability that an agent invokes. Skills
declare the *capabilities* they require (see
:class:`aios.agents.capability_catalog.CapabilityCatalog`) and the *permissions*
those capabilities map to (frozen :class:`aios.agents.permissions.Permission`).

Layering (ADR-0019)::

    Agent → Skill → Capability → Permission (frozen) → Connector → Integration

Skills orchestrate capabilities; they do not implement tools directly.
"""

from __future__ import annotations

from aios.skills.base import Skill, SkillContext, SkillResult, SkillStatus
from aios.skills.builtin import register_builtins
from aios.skills.executor import SkillExecutor
from aios.skills.loader import load_skill, load_skill_dir
from aios.skills.manifest import SkillManifest, SkillRetryPolicy
from aios.skills.planner import SkillPlanner
from aios.skills.registry import SkillRegistry
from aios.skills.validator import validate_skill_manifest

API_VERSION = "1.0"

__all__ = [
    "API_VERSION",
    "Skill",
    "SkillContext",
    "SkillExecutor",
    "SkillManifest",
    "SkillPlanner",
    "SkillRegistry",
    "SkillResult",
    "SkillRetryPolicy",
    "SkillStatus",
    "load_skill",
    "load_skill_dir",
    "register_builtins",
    "validate_skill_manifest",
]
