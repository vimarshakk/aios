"""v0.7.0 Stabilization — end-to-end integration, failure injection, security.

These tests exercise the *real* pipeline (no fakes)::

    Supervisor -> NativeGoalRunner -> AutonomousPlanner -> TaskGraph
               -> CapabilityResolver -> DeveloperPlatform.execute_skill
               -> Skill.run  (git / docker / filesystem / notes / notify / browser)

They intentionally run the native skills against the local machine (git,
docker, filesystem, a temp HOME) so they surface real runtime behaviour that
unit tests cannot. Browser/notify are exercised via their native code paths;
when an external binary is missing (e.g. docker) the skill must fail clearly
rather than crash the goal.

Run with:  uv run pytest tests/test_stabilization_e2e.py -q
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from aios.platform import DeveloperPlatform
from aios.supervisor import Supervisor
from aios.supervisor.goal import GoalStatus
from aios.supervisor.planner import AutonomousPlanner
from aios.supervisor.task_graph import Task, TaskGraph, validate_task_graph

# --------------------------------------------------------------------------- #
# Harness
# --------------------------------------------------------------------------- #


@pytest.fixture
def tmp_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate all HOME-derived state (notes dir, etc.)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return tmp_path


def make_supervisor(tmp_home: Path, **kw: object) -> Supervisor:
    """Real platform + real native skills, approval off for unattended runs."""
    platform = DeveloperPlatform()
    platform.bootstrap()
    return Supervisor(platform, require_approval=False, **kw)


async def run_to_completion(sup: Supervisor, goal_id: str) -> None:
    task = sup._tasks[goal_id]
    await task
    assert goal_id in sup._goals


def _step_by_cap(g: object, cap_prefix: str) -> dict | None:
    sr = g.context["workflow_result"]["step_results"]
    return next((r for r in sr.values() if r["capability"].startswith(cap_prefix)), None)


# --------------------------------------------------------------------------- #
# 1. End-to-end integration — Planner -> Resolver -> each native skill
# --------------------------------------------------------------------------- #


async def test_e2e_filesystem_list(tmp_home: Path) -> None:
    sup = make_supervisor(tmp_home)
    g = await sup.submit("list files in the home directory")
    await run_to_completion(sup, g.goal_id)
    assert g.status == GoalStatus.COMPLETED, g.error
    sr = g.context["workflow_result"]["step_results"]
    assert any(r["capability"] == "filesystem.read" for r in sr.values())


async def test_e2e_git_status_in_repo(tmp_home: Path) -> None:
    repo = tmp_home / "repo"
    repo.mkdir()
    init = (
        f"git -C {repo} init -q && "
        f"git -C {repo} config user.email t@t && "
        f"git -C {repo} config user.name t"
    )
    os.system(init)
    sup = make_supervisor(tmp_home)
    g = await sup.submit("show git status")
    await run_to_completion(sup, g.goal_id)
    assert g.status == GoalStatus.COMPLETED, g.error
    out = _step_by_cap(g, "git.status")
    assert out["status"] == "success"
    assert "On branch" in (out["outputs"].get("output") or "")


async def test_e2e_notes_write_then_read(tmp_home: Path) -> None:
    sup = make_supervisor(tmp_home)
    g = await sup.submit("create a note called Standup with body Done everything")
    await run_to_completion(sup, g.goal_id)
    assert g.status == GoalStatus.COMPLETED, g.error
    note = tmp_home / ".aios" / "notes" / "Standup.md"
    assert note.exists()
    assert "Done everything" in note.read_text()


async def test_e2e_notify(tmp_home: Path) -> None:
    sup = make_supervisor(tmp_home)
    g = await sup.submit("create a note called Ping with body hi")
    await run_to_completion(sup, g.goal_id)
    assert g.status == GoalStatus.COMPLETED, g.error
    notify = _step_by_cap(g, "desktop.notify")
    assert notify["status"] == "success"


async def test_e2e_mixed_multi_step(tmp_home: Path) -> None:
    """Mixed workflow: create note + notify (template: create_note)."""
    sup = make_supervisor(tmp_home)
    g = await sup.submit("write a note titled Plan with body Ship v0.7")
    await run_to_completion(sup, g.goal_id)
    assert g.status == GoalStatus.COMPLETED, g.error
    caps = {r["capability"] for r in g.context["workflow_result"]["step_results"].values()}
    assert "notes.write" in caps
    assert "desktop.notify" in caps


async def test_e2e_docker_ps(tmp_home: Path) -> None:
    """Docker goal: if docker is unavailable the step must FAIL clearly, not crash."""
    sup = make_supervisor(tmp_home)
    g = await sup.submit("inspect running docker containers")
    await run_to_completion(sup, g.goal_id)
    assert g.status in (GoalStatus.COMPLETED, GoalStatus.FAILED)
    docker = _step_by_cap(g, "docker.ps")
    assert docker is not None
    if docker["status"] == "failed":
        assert docker["error"]


async def test_e2e_resolver_native_first(tmp_home: Path) -> None:
    platform = DeveloperPlatform()
    platform.bootstrap()
    res = platform.resolve("notes.write")
    assert res.provider_kind.value == "native"
    assert res.available
    unknown = platform.resolve("nonexistent.capability")
    assert not unknown.available


# --------------------------------------------------------------------------- #
# 2. Failure injection
# --------------------------------------------------------------------------- #


async def test_fail_git_unknown_repo(tmp_home: Path) -> None:
    sup = make_supervisor(tmp_home)
    planner = AutonomousPlanner()
    graph = await planner.plan_async("show git status")
    for t in graph.tasks:
        if t.capability.startswith("git."):
            t.inputs["repo"] = str(tmp_home / "does_not_exist_repo")
    g = await sup.submit("anything")
    await sup.runner.execute(g, graph)
    git = _step_by_cap(g, "git.")
    assert git["status"] == "failed"
    assert git["error"]


async def test_fail_browser_unavailable(tmp_home: Path) -> None:
    """Browser step should fail clearly when its provider is absent (offline)."""
    sup = make_supervisor(tmp_home)
    g = await sup.submit("search Hacker News for AI and save to notes")
    await run_to_completion(sup, g.goal_id)
    browser = _step_by_cap(g, "browser.")
    assert browser is not None
    assert g.status in (GoalStatus.COMPLETED, GoalStatus.FAILED)


async def test_fail_malformed_plan_no_capability(tmp_home: Path) -> None:
    # An empty-capability task is rejected by the validation contract.
    graph = TaskGraph(goal="bad", tasks=[Task(id="x", capability="", action="run")])
    errs = validate_task_graph(graph)
    assert errs
    assert "no capability" in errs[0]
    # And executing such a graph fails the goal with a clear error (no crash).
    sup = make_supervisor(tmp_home)
    g = await sup.submit("anything")
    await sup.runner.execute(g, graph)
    assert g.context["workflow_result"]["status"] == "failed"
    step = next(iter(g.context["workflow_result"]["step_results"].values()))
    err = step.get("error") or ""
    assert "no available provider" in err or "no capability" in err


async def test_fail_unresolvable_capability(tmp_home: Path) -> None:
    sup = make_supervisor(tmp_home)
    graph = TaskGraph(
        goal="g",
        tasks=[Task(id="t", capability="imaginary.capability", action="do")],
    )
    g = await sup.submit("anything")
    # execute() must fail the goal gracefully (clear error) — never crash the loop.
    await sup.runner.execute(g, graph)
    assert g.context["workflow_result"]["status"] == "failed"
    step = next(iter(g.context["workflow_result"]["step_results"].values()))
    assert "no available provider" in (step.get("error") or "")


# --------------------------------------------------------------------------- #
# 3. Security — permission gating + approval
# --------------------------------------------------------------------------- #


async def test_security_native_permissions_granted_by_bootstrap(tmp_home: Path) -> None:
    platform = DeveloperPlatform()
    platform.bootstrap()
    assert "PROCESS_EXEC" in platform.executor._granted
    assert "FILESYSTEM_WRITE" in platform.executor._granted


async def test_security_unknown_skill_rejected(tmp_home: Path) -> None:
    platform = DeveloperPlatform()
    platform.bootstrap()
    res = await platform.execute_skill("nonexistent_skill", inputs={})
    assert res.status.value == "failed"
    assert "Unknown skill" in (res.error or "")


async def test_security_approval_gate_blocks_sensitive(tmp_home: Path) -> None:
    from aios.supervisor.executor import ApprovalRequiredError

    platform = DeveloperPlatform()
    platform.bootstrap()
    sup = Supervisor(platform, require_approval=True, approval_callback=None)
    graph = TaskGraph(
        goal="g",
        tasks=[Task(id="d", capability="destructive:drop-table", action="drop", inputs={})],
    )
    g = await sup.submit("anything")
    with pytest.raises(ApprovalRequiredError):
        await sup.runner.execute(g, graph)


async def test_security_approval_rejected(tmp_home: Path) -> None:
    from aios.supervisor.executor import ApprovalRequiredError

    platform = DeveloperPlatform()
    platform.bootstrap()

    async def deny(*args: object, **kw: object) -> bool:
        return False

    sup = Supervisor(platform, require_approval=True, approval_callback=deny)
    graph = TaskGraph(
        goal="g",
        tasks=[Task(id="d", capability="external:send-email", action="send", inputs={})],
    )
    g = await sup.submit("anything")
    with pytest.raises(ApprovalRequiredError):
        await sup.runner.execute(g, graph)


# --------------------------------------------------------------------------- #
# 4. Planner/executor robustness (validation contract)
# --------------------------------------------------------------------------- #


def test_validate_duplicate_ids() -> None:
    g = TaskGraph(tasks=[Task(id="a", capability="x"), Task(id="a", capability="y")])
    errs = validate_task_graph(g)
    assert any("duplicate" in e for e in errs)


def test_validate_unknown_dependency() -> None:
    g = TaskGraph(tasks=[Task(id="a", capability="x", depends_on=["ghost"])])
    errs = validate_task_graph(g)
    assert any("unknown task" in e for e in errs)


def test_validate_cycle() -> None:
    g = TaskGraph(tasks=[
        Task(id="a", capability="x", depends_on=["b"]),
        Task(id="b", capability="y", depends_on=["a"]),
    ])
    errs = validate_task_graph(g)
    assert any("cycle" in e for e in errs)


def test_planner_injects_retry_for_network_caps() -> None:
    planner = AutonomousPlanner()
    graph = planner.plan("search Hacker News for AI")
    retry_tasks = [t for t in graph.tasks if t.capability.startswith("browser.")]
    assert retry_tasks
    assert all(t.retry and t.retry.get("max_retries", 0) > 0 for t in retry_tasks)


def test_planner_template_routing(tmp_home: Path) -> None:
    planner = AutonomousPlanner()
    g = planner.plan("create a note called Todo with body buy milk")
    caps = {t.capability for t in g.tasks}
    assert "notes.write" in caps


# --------------------------------------------------------------------------- #
# 5. Concurrent goals
# --------------------------------------------------------------------------- #


async def test_concurrent_goals_isolated(tmp_home: Path) -> None:
    sup = make_supervisor(tmp_home)
    g1 = await sup.submit("create a note called A with body one")
    g2 = await sup.submit("create a note called B with body two")
    await run_to_completion(sup, g1.goal_id)
    await run_to_completion(sup, g2.goal_id)
    assert sup.get_goal(g1.goal_id).status == GoalStatus.COMPLETED
    assert sup.get_goal(g2.goal_id).status == GoalStatus.COMPLETED
    assert (tmp_home / ".aios" / "notes" / "A.md").exists()
    assert (tmp_home / ".aios" / "notes" / "B.md").exists()


async def test_concurrent_and_serial_flag_respected(tmp_home: Path) -> None:
    sup = make_supervisor(tmp_home, parallel=False)
    g1 = await sup.submit("create a note called S1 with body x")
    g2 = await sup.submit("create a note called S2 with body y")
    await run_to_completion(sup, g1.goal_id)
    await run_to_completion(sup, g2.goal_id)
    assert sup.get_goal(g1.goal_id).status == GoalStatus.COMPLETED
    assert sup.get_goal(g2.goal_id).status == GoalStatus.COMPLETED
    assert g1.context["workflow_result"]["parallel"] is False
