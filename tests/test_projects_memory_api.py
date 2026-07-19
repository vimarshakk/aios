"""Tests for Projects and Memory API endpoints on the gateway (M7.3).

Verifies routes are registered and basic wiring works.
"""

from __future__ import annotations

import pytest

from aios.gateway.main import app


def _paths() -> set[str]:
    return {route.path for route in app.routes}


# -------------------------------------------------------------------------
# Projects
# -------------------------------------------------------------------------


def test_projects_routes_registered() -> None:
    paths = _paths()
    assert "/projects" in paths
    assert "/projects/{project_id}" in paths
    assert "/projects/scan" in paths


def test_project_model_fields() -> None:
    from aios.gateway.main import ProjectInfo

    p = ProjectInfo(
        id="test",
        name="Test",
        path="/tmp",
        description="A test project",
        last_accessed="1h ago",
        status="active",
        goal_count=0,
        languages=["python"],
        file_count=10,
    )
    assert p.id == "test"
    assert p.languages == ["python"]


def test_scan_projects_finds_git_repos(tmp_path: pytest.PathLike) -> None:
    """_scan_projects should discover git repos in a directory."""
    import subprocess

    from aios.gateway.main import _scan_projects

    # Create a fake git repo
    repo = tmp_path / "test-repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], capture_output=True)
    projects = _scan_projects(str(tmp_path))
    assert any(p.name == "test-repo" for p in projects)


def test_relative_time() -> None:
    from aios.gateway.main import _relative_time
    import time

    assert _relative_time(None) == ""
    assert _relative_time(time.time() - 5) == "just now"
    assert _relative_time(time.time() - 120) == "2m ago"
    assert _relative_time(time.time() - 7200) == "2h ago"
    assert _relative_time(time.time() - 172800) == "2d ago"


# -------------------------------------------------------------------------
# Memory
# -------------------------------------------------------------------------


def test_memory_routes_registered() -> None:
    paths = _paths()
    assert "/memory/remember" in paths
    assert "/memory/search" in paths
    assert "/memory/recent" in paths
    assert "/memory/timeline" in paths


def test_memory_model_fields() -> None:
    from aios.gateway.main import MemoryEntry

    m = MemoryEntry(
        id="abc123",
        content="Test memory",
        type="fact",
        tags=["test"],
        created_at="just now",
        confidence=0.95,
        source="conversation",
    )
    assert m.id == "abc123"
    assert m.confidence == 0.95


def test_remember_request_model() -> None:
    from aios.gateway.main import RememberRequest

    r = RememberRequest(content="Remember this", tags=["test"], type="fact")
    assert r.content == "Remember this"
    assert r.tags == ["test"]


@pytest.mark.asyncio
async def test_memory_store_and_search() -> None:
    """Store a memory via the manager and retrieve it."""
    from aios.gateway.main import _get_memory

    mem = _get_memory()
    doc_id = await mem.store("AIOS runs on Ollama with qwen3", metadata={"tags": ["config"], "type": "fact"})
    assert doc_id

    results = await mem.retrieve("Ollama", top_k=5)
    assert len(results) >= 1
    assert any("Ollama" in r.content for r in results)


@pytest.mark.asyncio
async def test_episodic_recent() -> None:
    """Store episodic memories and verify recent retrieval."""
    from aios.gateway.main import _get_memory
    from aios.memory import EpisodicMemory

    mem = _get_memory()
    backend = mem.get_backend("episodic")
    assert isinstance(backend, EpisodicMemory)

    await mem.store("First memory", metadata={"type": "fact"})
    await mem.store("Second memory", metadata={"type": "fact"})

    recent = backend.get_recent(10)
    assert len(recent) >= 2
    assert recent[-1].content == "Second memory"
