"""Tests for aios.skills — registry, manifest, executor, planner, validator, loader."""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from aios.skills.base import (
    Skill,
    SkillContext,
    SkillResult,
    SkillStatus,
)
from aios.skills.builtin import register_builtins
from aios.skills.executor import SkillExecutor
from aios.skills.manifest import SkillManifest, SkillRetryPolicy
from aios.skills.planner import SkillPlanner
from aios.skills.registry import SkillRegistry
from aios.skills.validator import validate_skill_manifest


class _EchoSkill(Skill):
    def __init__(self, name: str = "echo", perms: tuple[str, ...] = ()) -> None:
        super().__init__(
            SkillManifest(
                name=name,
                description="Echo back inputs",
                inputs=("msg",),
                outputs=("out",),
                capabilities=("filesystem.read",),
                permissions=perms,
                tags=("test",),
            )
        )

    async def run(self, ctx: SkillContext) -> SkillResult:
        msg = ctx.inputs.get("msg")
        if not msg:
            return SkillResult(status=SkillStatus.FAILED, error="no msg")
        return SkillResult(
            status=SkillStatus.SUCCESS,
            outputs={"out": msg},
            steps=["echo"],
            data=msg,
        )


class TestSkillRegistry:
    def test_register_and_get(self) -> None:
        reg = SkillRegistry()
        reg.register(_EchoSkill())
        assert reg.has("echo")
        assert reg.get("echo") is not None
        assert reg.get("missing") is None
        assert "echo" in reg
        assert len(reg) == 1

    def test_register_duplicate_raises(self) -> None:
        reg = SkillRegistry()
        reg.register(_EchoSkill())
        with pytest.raises(ValueError, match="already registered"):
            reg.register(_EchoSkill())

    def test_unregister(self) -> None:
        reg = SkillRegistry()
        reg.register(_EchoSkill())
        removed = reg.unregister("echo")
        assert removed is not None
        assert reg.count == 0
        assert reg.unregister("echo") is None

    def test_by_capability(self) -> None:
        reg = SkillRegistry()
        reg.register(_EchoSkill())
        found = reg.by_capability("filesystem.read")
        assert [s.name for s in found] == ["echo"]

    def test_by_tag_and_find(self) -> None:
        reg = SkillRegistry()
        reg.register(_EchoSkill())
        assert [s.name for s in reg.by_tag("test")] == ["echo"]
        assert [s.name for s in reg.find("echo")] == ["echo"]
        assert reg.find("nonexistent") == []

    def test_stats_and_clear(self) -> None:
        reg = SkillRegistry()
        reg.register(_EchoSkill())
        stats = reg.stats()
        assert stats.total == 1
        assert stats.by_tag.get("test") == 1
        assert reg.clear() == 1
        assert reg.count == 0

    def test_manifests(self) -> None:
        reg = SkillRegistry()
        reg.register(_EchoSkill())
        assert len(reg.manifests()) == 1


class TestSkillExecutor:
    async def test_execute_success(self) -> None:
        skill = _EchoSkill()
        ex = SkillExecutor(granted_permissions=[])
        result = await ex.execute(skill, inputs={"msg": "hi"})
        assert result.ok
        assert result.outputs["out"] == "hi"
        assert len(ex.history) == 1

    async def test_execute_missing_permission(self) -> None:
        skill = _EchoSkill(perms=("FILESYSTEM_READ",))
        ex = SkillExecutor(granted_permissions=[])
        result = await ex.execute(skill, inputs={"msg": "hi"})
        assert result.status == SkillStatus.FAILED
        assert "FILESYSTEM_READ" in result.error

    async def test_execute_with_granted_permission(self) -> None:
        skill = _EchoSkill(perms=("FILESYSTEM_READ",))
        ex = SkillExecutor(granted_permissions=["FILESYSTEM_READ"])
        result = await ex.execute(skill, inputs={"msg": "ok"})
        assert result.ok

    async def test_retry_on_failure(self) -> None:
        class Flaky(Skill):
            def __init__(self) -> None:
                super().__init__(
                    SkillManifest(
                        name="flaky",
                        retry=SkillRetryPolicy(max_attempts=3, backoff_seconds=0.0),
                    )
                )

            async def run(self, ctx: SkillContext) -> SkillResult:
                ctx.state.setdefault("n", 0)
                ctx.state["n"] += 1
                if ctx.state["n"] < 3:
                    return SkillResult(status=SkillStatus.FAILED, error="boom")
                return SkillResult(status=SkillStatus.SUCCESS)

        ex = SkillExecutor()
        result = await ex.execute(Flaky())
        assert result.ok
        assert ex.history[-1].attempts == 3

    async def test_non_retryable(self) -> None:
        class HardFail(Skill):
            def __init__(self) -> None:
                super().__init__(
                    SkillManifest(
                        name="hard",
                        retry=SkillRetryPolicy(
                            max_attempts=3, non_retryable=("fatal",)
                        ),
                    )
                )

            async def run(self, ctx: SkillContext) -> SkillResult:
                return SkillResult(status=SkillStatus.FAILED, error="fatal error")

        ex = SkillExecutor()
        result = await ex.execute(HardFail())
        assert not result.ok
        assert ex.history[-1].attempts == 1


class TestSkillPlanner:
    def test_plan_for_capabilities_orders_by_coverage(self) -> None:
        reg = SkillRegistry()
        reg.register(_EchoSkill(name="specific"))
        broad = _EchoSkill(name="broad")
        broad._manifest = SkillManifest(  # type: ignore[attr-defined]
            name="broad",
            capabilities=("filesystem.read", "filesystem.write"),
            tags=("test",),
        )
        reg.register(broad)
        planner = SkillPlanner(reg)
        plan = planner.plan_for_capabilities(
            ["filesystem.read", "filesystem.write"]
        )
        assert plan.skills == ["broad", "specific"]
        assert not plan.empty

    def test_plan_empty(self) -> None:
        reg = SkillRegistry()
        planner = SkillPlanner(reg)
        assert planner.plan_for_capabilities(["x"]).empty


class TestSkillValidator:
    def test_valid_manifest(self) -> None:
        m = SkillManifest(
            name="code-review",
            description="Review code",
            approval="ask_once",
        )
        report = validate_skill_manifest(m)
        assert report.valid
        assert report.errors == []

    def test_invalid_approval(self) -> None:
        m = SkillManifest(name="x", approval="maybe")
        report = validate_skill_manifest(m)
        assert not report.valid
        assert any(i.field == "approval" for i in report.errors)

    def test_warning_for_non_kebab(self) -> None:
        m = SkillManifest(name="CodeReview", description="d", approval="allow")
        report = validate_skill_manifest(m)
        assert report.valid  # warning only
        assert report.warnings

    def test_retry_validation(self) -> None:
        m = SkillManifest(
            name="x", approval="allow",
            retry=SkillRetryPolicy(max_attempts=0),
        )
        report = validate_skill_manifest(m)
        assert any(i.field == "retry.max_attempts" for i in report.errors)


class TestBuiltinSkills:
    def test_register_builtins(self) -> None:
        reg = SkillRegistry()
        register_builtins(reg)
        assert reg.has("code-review")
        assert reg.has("web-research")
        assert "filesystem.read" in reg.get("code-review").manifest.capabilities

    async def test_builtin_runs(self) -> None:
        reg = SkillRegistry()
        register_builtins(reg)
        skill = reg.get("web-research")
        ex = SkillExecutor(granted_permissions=["NETWORK_HTTP"])
        result = await ex.execute(skill, inputs={"query": "aios"})
        assert result.ok


class TestSkillLoader:
    def test_load_skill_yaml(self, tmp_path: Path) -> None:
        from aios.skills.loader import load_skill

        p = tmp_path / "my-skill.yaml"
        p.write_text(
            textwrap.dedent(
                """
                name: my-skill
                version: 2.0.0
                description: demo
                capabilities: [filesystem.read]
                permissions: [FILESYSTEM_READ]
                approval: ask_once
                tags: [demo]
                """
            )
        )
        m = load_skill(p)
        assert m.name == "my-skill"
        assert m.version == "2.0.0"
        assert m.permissions == ("FILESYSTEM_READ",)
        assert m.tags == ("demo",)

    def test_load_skill_missing_file(self, tmp_path: Path) -> None:
        from aios.skills.loader import load_skill

        with pytest.raises(FileNotFoundError):
            load_skill(tmp_path / "nope.yaml")

    def test_load_skill_missing_name(self, tmp_path: Path) -> None:
        from aios.skills.loader import load_skill

        p = tmp_path / "bad.yaml"
        p.write_text("description: no name\n")
        with pytest.raises(ValueError, match="name"):
            load_skill(p)

    def test_load_skill_dir(self, tmp_path: Path) -> None:
        from aios.skills.loader import load_skill_dir

        (tmp_path / "a.yaml").write_text("name: a\napproval: allow\n")
        (tmp_path / "b.yml").write_text("name: b\napproval: allow\n")
        (tmp_path / "note.txt").write_text("ignore me")
        manifests = load_skill_dir(tmp_path)
        names = sorted(m.name for m in manifests)
        assert names == ["a", "b"]
