"""Tests for aios.workspaces — isolated execution contexts."""

from __future__ import annotations

import pytest

from aios.artifacts import ArtifactKind, ArtifactStore, MemoryArtifactBackend
from aios.secrets import MemoryBackend, SecretStore
from aios.security.encryption import VaultEncryptor
from aios.skills.registry import SkillRegistry
from aios.workspaces import Workspace, WorkspaceConfig, WorkspaceManager
from aios.workspaces.subsystems import (
    WorkspaceCache,
    WorkspaceHistory,
    WorkspaceMemory,
    WorkspacePermissions,
)


@pytest.fixture
def skills() -> SkillRegistry:
    from aios.skills.builtin import register_builtins

    reg = SkillRegistry()
    register_builtins(reg)
    return reg


@pytest.fixture
def secrets() -> SecretStore:
    return SecretStore(
        VaultEncryptor.from_password("master"), backend=MemoryBackend()
    )


@pytest.fixture
def artifacts() -> ArtifactStore:
    return ArtifactStore(MemoryArtifactBackend())


class TestWorkspace:
    def test_root_and_name(self, tmp_path) -> None:
        ws = Workspace(
            WorkspaceConfig(id="w1", name="Main", root=str(tmp_path / "w1"))
        )
        assert ws.id == "w1"
        assert ws.name == "Main"
        assert ws.root == tmp_path / "w1"

    def test_ensure_root_creates_dir(self, tmp_path) -> None:
        ws = Workspace(WorkspaceConfig(id="w2", root=str(tmp_path / "deep" / "w2")))
        root = ws.ensure_root()
        assert root.is_dir()

    def test_resolve_skills(self, skills) -> None:
        ws = Workspace(
            WorkspaceConfig(id="w3", skill_names=("code-review", "missing-skill")),
            skills=skills,
        )
        resolved = ws.resolve_skills()
        names = {s.name for s in resolved}
        assert "code-review" in names
        assert "missing-skill" not in names
        assert ws.has_skill("code-review")
        assert not ws.has_skill("missing-skill")

    def test_assigned_skill_names(self) -> None:
        ws = Workspace(WorkspaceConfig(id="w4", skill_names=("a", "b")))
        assert ws.assigned_skill_names == ["a", "b"]

    def test_scoped_secrets(self, secrets) -> None:
        ws = Workspace(
            WorkspaceConfig(id="w5", secret_prefix="WS_"),  # noqa: S106
            secrets=secrets,
        )
        ws.put_scoped_secret("token", "abc123")
        assert ws.scoped_secret("token") == "abc123"
        assert ws.scoped_secret("other") is None

    def test_scoped_secret_without_store(self) -> None:
        ws = Workspace(WorkspaceConfig(id="w6"))
        assert ws.scoped_secret("token") is None


class TestWorkspaceManager:
    def test_create_and_get(self, tmp_path, skills) -> None:
        mgr = WorkspaceManager()
        ws = mgr.create(
            WorkspaceConfig(id="a", root=str(tmp_path / "a")),
            skills=skills,
        )
        assert mgr.get("a") is ws
        assert "a" in mgr
        assert mgr.ids == ["a"]

    def test_duplicate_raises(self, tmp_path) -> None:
        mgr = WorkspaceManager()
        mgr.create(WorkspaceConfig(id="a", root=str(tmp_path / "a")))
        with pytest.raises(ValueError, match="already exists"):
            mgr.create(WorkspaceConfig(id="a", root=str(tmp_path / "b")))

    def test_remove(self, tmp_path) -> None:
        mgr = WorkspaceManager()
        mgr.create(WorkspaceConfig(id="a", root=str(tmp_path / "a")))
        removed = mgr.remove("a")
        assert removed is not None
        assert mgr.get("a") is None
        assert len(mgr) == 0


class TestWorkspaceSubsystems:
    def test_memory(self) -> None:
        mem = WorkspaceMemory()
        mem.set("k", 1)
        assert mem.get("k") == 1
        assert mem.get("missing", "d") == "d"
        assert mem.delete("k") is True
        assert mem.keys() == []

    def test_history_append_only(self) -> None:
        hist = WorkspaceHistory()
        e1 = hist.record("init", "started")
        e2 = hist.record("plan", "made plan")
        assert len(hist.entries) == 2
        assert hist.entries[0] is e1
        assert e2.action == "plan"
        assert len(hist.since(e2.timestamp)) == 1

    def test_cache(self) -> None:
        cache = WorkspaceCache()
        cache.put("a", 1)
        assert cache.get("a") == 1
        assert cache.invalidate("a") is True
        assert cache.get("a") is None

    def test_permissions(self) -> None:
        perms = WorkspacePermissions(granted=("filesystem.read",))
        assert perms.allows("filesystem.read")
        assert not perms.allows("filesystem.write")
        merged = perms.union(WorkspacePermissions(granted=("filesystem.write",)))
        assert merged.allows("filesystem.write")

    def test_workspace_exposes_subsystems(self, tmp_path, artifacts) -> None:
        ws = Workspace(
            WorkspaceConfig(id="wsx", root=str(tmp_path / "wsx")),
            artifacts=artifacts,
        )
        ws.memory.set("note", "hi")
        assert ws.memory.get("note") == "hi"
        ws.history.record("step", "did thing")
        assert len(ws.history.entries) == 1
        ws.cache.put("cached", 42)
        assert ws.cache.get("cached") == 42
        ws.permissions = WorkspacePermissions(granted=("network.http",))
        assert ws.permissions.allows("network.http")
        assert ws.artifacts is not None
        art = ws.artifacts.save("doc", "# note", kind=ArtifactKind.MARKDOWN)
        assert art.kind.value == "markdown"


class TestWorkspaceArtifacts:
    def test_scoped_save_marks_workspace(self, tmp_path, artifacts) -> None:
        ws = Workspace(
            WorkspaceConfig(id="wsa", root=str(tmp_path / "wsa")),
            artifacts=artifacts,
        )
        art = ws.artifacts.save("report", b"data", kind=ArtifactKind.REPORT)
        loaded = artifacts.get(art.id)
        assert loaded is not None
        assert loaded.metadata.get("workspace") == "wsa"
