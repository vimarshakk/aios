"""Skill loader — load skills from YAML manifests or modules."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import os

import yaml

from aios.skills.base import Skill
from aios.skills.manifest import SkillManifest, SkillRetryPolicy


def _load_retry(data: dict[str, Any]) -> SkillRetryPolicy:
    raw = data.get("retry") or {}
    non_retryable = raw.get("non_retryable") or []
    return SkillRetryPolicy(
        max_attempts=int(raw.get("max_attempts", 1)),
        backoff_seconds=float(raw.get("backoff_seconds", 1.0)),
        non_retryable=tuple(non_retryable),
    )


def load_skill(path: str | os.PathLike[str]) -> SkillManifest:
    """Load a :class:`SkillManifest` from a YAML file.

    The YAML file must contain at least ``name``; other fields are optional.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Skill manifest not found: {path}")
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    name = data.get("name")
    if not name:
        raise ValueError(f"Skill manifest '{path}' missing required 'name'")

    return SkillManifest(
        name=str(name),
        version=str(data.get("version", "1.0.0")),
        description=str(data.get("description", "")),
        inputs=tuple(data.get("inputs", ())),
        outputs=tuple(data.get("outputs", ())),
        capabilities=tuple(data.get("capabilities", ())),
        permissions=tuple(data.get("permissions", ())),
        prompts=tuple(data.get("prompts", ())),
        retry=_load_retry(data),
        approval=str(data.get("approval", "ask_once")),
        tags=tuple(data.get("tags", ())),
        metadata=dict(data.get("metadata", {})),
    )


def load_skill_dir(directory: str | os.PathLike[str]) -> list[SkillManifest]:
    """Load all ``*.yaml`` / ``*.yml`` skill manifests in a directory."""
    d = Path(directory)
    if not d.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    return [
        load_skill(entry)
        for entry in sorted(d.glob("*.y*ml"))
        if entry.is_file()
    ]


def load_skill_module(path: str | os.PathLike[str]) -> Skill:
    """Load a :class:`Skill` subclass instance from a Python module file.

    The module must expose a module-level ``skill`` (a :class:`Skill` instance)
    or a ``Skill`` subclass named ``SkillImpl``.
    """
    p = Path(path)
    spec = importlib.util.spec_from_file_location("_aios_skill_mod", p)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import skill module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "skill") and isinstance(module.skill, Skill):
        return module.skill
    if hasattr(module, "SkillImpl") and isinstance(module.SkillImpl, type) \
            and issubclass(module.SkillImpl, Skill):
        return module.SkillImpl()
    raise ValueError(
        f"Skill module '{path}' must define `skill` or `SkillImpl`"
    )


__all__ = ["load_skill", "load_skill_dir", "load_skill_module"]
