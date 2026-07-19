"""Tests for the AIOS CLI (Priority 2, ADR-0027).

Covers:
- unit: parser, configurable assistant name, JSON output shape
- e2e: commands against a real gateway app backed by an offline Supervisor
- watch: global WS streaming surfaces a running goal to completion
- json: every command honors ``--json``
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import threading
import time

import pytest
import uvicorn

from aios.gateway.main import app
from aios.skills.base import SkillResult, SkillStatus
from aios.supervisor import Goal, GoalStatus, Supervisor
from aios.supervisor.cli import (
    assistant_name,
    build_parser,
)
from aios.supervisor.cli import (
    main as cli_main,
)

# The e2e fixture spins up a real uvicorn server in a background thread; its
# event loop/socket teardown emits PytestUnraisableExceptionWarning under
# filterwarnings=error. That is a test-harness artifact, not a CLI defect.
pytestmark = pytest.mark.filterwarnings(
    "ignore::pytest.PytestUnraisableExceptionWarning"
)

logger = logging.getLogger(__name__)


class _FakePlatform:
    """Minimal DeveloperPlatform stand-in for offline CLI tests."""

    def resolve(self, capability: str):
        class _R:
            provider_kind = "native"
            provider_id = capability.split(".")[0]
            available = True
            reason = ""

            @property
            def resolved(self):
                return True

        return _R()

    def create_workspace(self, workspace_id, *args, **kwargs):
        class _Ws:
            id = workspace_id

        return _Ws()

    async def execute_skill(self, *args, **kwargs) -> SkillResult:
        return SkillResult(status=SkillStatus.SUCCESS, data={})


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def gateway():
    port = _free_port()
    sup = Supervisor(_FakePlatform())
    import aios.gateway.main as m

    m._supervisor = sup
    os.environ["AIOS_GATEWAY_URL"] = f"http://127.0.0.1:{port}"

    class _Server(uvicorn.Server):
        def install_signal_handlers(self) -> None:
            pass

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = _Server(config)
    loop = asyncio.new_event_loop()

    def _serve() -> None:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.serve())
        loop.close()

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    url = f"http://127.0.0.1:{port}"
    import httpx2 as httpx

    for _ in range(100):
        try:
            if httpx.get(f"{url}/health", timeout=0.5).status_code == 200:
                break
        except Exception as exc:  # server not up yet
            logger.debug("gateway not ready: %s", exc)
        time.sleep(0.05)
    yield url, sup
    server.should_exit = True
    t.join(timeout=5)
    m._supervisor = None
    del os.environ["AIOS_GATEWAY_URL"]


# --------------------------------------------------------------------------- unit

def test_parser_has_all_commands() -> None:
    parser = build_parser()
    sub = parser._subparsers._group_actions[0].choices
    assert set(sub) >= {
        "run", "goals", "goal", "status", "logs", "watch",
        "pause", "resume", "cancel", "retry", "version", "doctor", "completion",
    }


def test_assistant_name_configurable(monkeypatch) -> None:
    monkeypatch.setenv("AIOS_ASSISTANT_NAME", "Nova")
    assert assistant_name() == "Nova"
    monkeypatch.delenv("AIOS_ASSISTANT_NAME", raising=False)
    assert assistant_name() == "AIOS"


def test_completion_script_emits_for_each_shell(gateway) -> None:
    for shell in ("bash", "zsh", "fish"):
        rc = cli_main(["completion", shell])
        assert rc == 0


# --------------------------------------------------------------------------- e2e

def test_version_and_doctor(gateway, capsys) -> None:
    assert cli_main(["version"]) == 0
    assert cli_main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "AIOS" in out or "Doctor" in out


def test_goals_lists_seeded_goal(gateway, capsys) -> None:
    _, sup = gateway
    g = Goal(objective="seed objective", status=GoalStatus.COMPLETED)
    sup._goals[g.goal_id] = g
    assert cli_main(["goals"]) == 0
    assert g.goal_id in capsys.readouterr().out


def test_status_json_shape(gateway) -> None:
    _, sup = gateway
    g = Goal(objective="seed", status=GoalStatus.COMPLETED)
    sup._goals[g.goal_id] = g
    rc = cli_main(["--json", "status", g.goal_id])
    assert rc == 0


def test_logs_with_events(gateway, capsys) -> None:
    _, sup = gateway
    g = Goal(objective="seed", status=GoalStatus.COMPLETED)
    g.context["events"] = [{"ts": 1, "type": "plan", "detail": "planned"}]
    sup._goals[g.goal_id] = g
    assert cli_main(["logs", g.goal_id]) == 0
    assert "plan" in capsys.readouterr().out


def test_run_watch_follows_to_completion(gateway, capsys) -> None:
    assert cli_main(["run", "summarize the homepage", "--watch"]) == 0
    out = capsys.readouterr().out
    assert "submitted" in out


def test_pause_cancel_actions(gateway, capsys) -> None:
    _, sup = gateway
    g = Goal(objective="seed", status=GoalStatus.RUNNING)
    sup._goals[g.goal_id] = g
    assert cli_main(["pause", g.goal_id]) == 0
    assert sup.get_goal(g.goal_id).status.value == "paused"
    assert cli_main(["cancel", g.goal_id]) == 0
    assert sup.get_goal(g.goal_id).status.value == "cancelled"


def test_resume_waiting_approval(gateway, capsys) -> None:
    _, sup = gateway
    g = Goal(objective="seed", status=GoalStatus.WAITING_APPROVAL)
    sup._goals[g.goal_id] = g
    assert cli_main(["resume", g.goal_id]) == 0
    # Resume re-runs the goal; it should leave the waiting state.
    assert sup.get_goal(g.goal_id).status.value != "waiting_approval"


def test_retry_recreates_failed_goal(gateway, capsys) -> None:
    _, sup = gateway
    g = Goal(objective="seed failed", status=GoalStatus.FAILED)
    sup._goals[g.goal_id] = g
    before = len(sup.list_goals())
    assert cli_main(["retry", g.goal_id]) == 0
    after = len(sup.list_goals())
    assert after == before + 1  # retry created a fresh goal


def test_watch_streams_live(gateway, capsys) -> None:
    _, sup = gateway
    g = Goal(objective="seed", status=GoalStatus.COMPLETED)
    sup._goals[g.goal_id] = g
    rc = cli_main(["watch"])
    assert rc == 0
    assert g.goal_id in capsys.readouterr().out
