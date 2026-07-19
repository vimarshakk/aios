"""Tests for AIOS-native desktop skills (offline-first)."""

from __future__ import annotations

from aios.skills.base import SkillContext, SkillStatus
from aios.skills.native import (
    FilesystemSkill,
    GitSkill,
    NotesSkill,
    TerminalSkill,
    register_native_skills,
)
from aios.skills.registry import SkillRegistry


async def test_terminal_runs_command() -> None:
    skill = TerminalSkill()
    res = await skill.run(
        SkillContext(skill_name="terminal", inputs={"command": "echo hello"})
    )
    assert res.status == SkillStatus.SUCCESS
    assert "hello" in (res.outputs.get("stdout") or "")


async def test_filesystem_list_and_search(tmp_path) -> None:
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.log").write_text("y")
    skill = FilesystemSkill()
    res = await skill.run(
        SkillContext(skill_name="filesystem", inputs={"action": "list", "path": str(tmp_path)})
    )
    assert res.status == SkillStatus.SUCCESS
    assert len(res.outputs["entries"]) == 2

    found = await skill.run(
        SkillContext(
            skill_name="filesystem",
            inputs={"action": "search", "path": str(tmp_path), "pattern": "*.log"},
        )
    )
    assert any(p.endswith("b.log") for p in found.outputs["entries"])


async def test_notes_write_read(tmp_path) -> None:
    skill = NotesSkill(notes_dir=str(tmp_path / "notes"))
    w = await skill.run(
        SkillContext(
            skill_name="notes",
            inputs={"action": "write", "title": "Idea", "body": "build JARVIS"},
        )
    )
    assert w.status == SkillStatus.SUCCESS
    r = await skill.run(
        SkillContext(skill_name="notes", inputs={"action": "read", "name": "Idea"})
    )
    assert r.status == SkillStatus.SUCCESS
    assert "build JARVIS" in r.outputs["content"]


async def test_git_status_in_repo(tmp_path) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=False)  # noqa: S603, S607
    skill = GitSkill()
    res = await skill.run(
        SkillContext(skill_name="git", inputs={"subcommand": "status", "repo": str(tmp_path)})
    )
    # git is available; even a fresh repo returns success with output.
    assert res.status == SkillStatus.SUCCESS


def test_register_native_skills_populates_registry_and_resolver() -> None:
    reg = SkillRegistry()
    from aios.platform import CapabilityResolver

    resolver = CapabilityResolver(skills=reg)
    register_native_skills(reg, resolver)
    names = reg.names
    for expected in ("terminal", "filesystem", "git", "docker", "notes", "notify"):
        assert expected in names
    # terminal.exec resolves to the native terminal skill.
    r = resolver.resolve("terminal.exec")
    assert r.provider_kind.value == "native"
    assert r.provider_id == "terminal"
