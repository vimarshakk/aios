"""Tests for the AIOS daemon (M5.3) and proactive briefing (M5.5)."""

from __future__ import annotations

import asyncio

from aios.platform import DeveloperPlatform, ProviderKind
from aios.supervisor import BriefingConfig, BriefingEngine, Daemon, DaemonConfig


def _platform() -> DeveloperPlatform:
    p = DeveloperPlatform()
    p.bootstrap()
    return p


def test_daemon_status_and_persistence(tmp_path) -> None:
    p = _platform()
    cfg = DaemonConfig(data_dir=str(tmp_path / "daemon"), persist=True)
    daemon = Daemon(p, cfg)
    status = daemon.status()
    assert status["goals"] == 0
    assert status["persist"] is True

    gid = asyncio.run(daemon.submit("Summarize today's work"))
    assert isinstance(gid, str)
    assert gid
    assert daemon.status()["goals"] >= 1
    # Persistence file written.
    assert (tmp_path / "daemon" / "daemon-state.json").exists()


def test_daemon_pause_cancel(tmp_path) -> None:
    import asyncio

    p = _platform()
    daemon = Daemon(p, DaemonConfig(data_dir=str(tmp_path / "d"), persist=False))
    # Insert a non-terminal goal directly so control methods are deterministic
    # (no background execution racing the assertions).
    from aios.supervisor import Goal, GoalStatus, StepRecord, Task, TaskGraph

    graph = TaskGraph(
        goal="Long task",
        tasks=[Task(id="t", capability="terminal.exec", action="run", inputs={"command": "true"})],
    )
    goal = Goal(objective="Long task", status=GoalStatus.PENDING)
    goal.context["task_graph"] = graph.to_dict()
    goal.steps = [StepRecord(step_index=0, skill="terminal")]
    daemon.supervisor._goals[goal.goal_id] = goal

    assert asyncio.run(daemon.pause(goal.goal_id)) is True
    assert goal.status == GoalStatus.PAUSED
    # Cancel from a non-terminal (paused) state succeeds.
    assert asyncio.run(daemon.cancel(goal.goal_id)) is True
    assert goal.status == GoalStatus.CANCELLED


async def test_daemon_resume_runs_goal(tmp_path) -> None:
    import asyncio

    p = _platform()
    daemon = Daemon(p, DaemonConfig(data_dir=str(tmp_path / "d2"), persist=False))
    from aios.supervisor import Goal, GoalStatus, StepRecord, Task, TaskGraph

    graph = TaskGraph(
        goal="Echo",
        tasks=[Task(id="t", capability="terminal.exec", action="run", inputs={"command": "true"})],
    )
    goal = Goal(objective="Echo", status=GoalStatus.PAUSED)
    goal.context["task_graph"] = graph.to_dict()
    goal.steps = [StepRecord(step_index=0, skill="terminal")]
    daemon.supervisor._goals[goal.goal_id] = goal

    # Run resume + the background goal within a single event loop so the goal
    # actually progresses to a terminal state.
    async def _drive() -> None:
        assert await daemon.resume(goal.goal_id) is True
        for _ in range(100):
            if goal.is_terminal:
                break
            await asyncio.sleep(0.02)

    await _drive()
    assert goal.is_terminal


def test_briefing_off_hours() -> None:
    engine = BriefingEngine(config=BriefingConfig(after_hour=99))
    assert engine.compose_objective() is None


def test_briefing_already_run() -> None:
    engine = BriefingEngine(config=BriefingConfig(after_hour=0))
    engine.last_run_date = engine.today()
    assert engine.compose_objective() is None


def test_briefing_compose_with_native_caps(tmp_path) -> None:
    p = _platform()
    engine = BriefingEngine(platform=p, config=BriefingConfig(after_hour=0))
    # Force native capabilities to resolve so sections are included.
    for cap in ("notes.read", "git.status", "filesystem.read"):
        p.register_provider(cap, "native", ProviderKind.NATIVE, None)

    objective = engine.compose_objective()
    assert objective is not None
    assert "Morning briefing" in objective
    assert "notes" in objective
    assert "git" in objective
    assert "Downloads" in objective


def test_briefing_announce_without_notify() -> None:
    engine = BriefingEngine(config=BriefingConfig(notify=False))
    asyncio.run(engine.announce("hi"))


def test_daemon_wires_briefing(tmp_path) -> None:
    p = _platform()
    engine = BriefingEngine(platform=p, config=BriefingConfig(after_hour=0))
    daemon = Daemon(p, DaemonConfig(data_dir=str(tmp_path / "d2"), briefing=engine))
    assert daemon.status()["briefing_enabled"] is True
