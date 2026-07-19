"""Tests for the gateway global goals WebSocket stream (Priority 1, ADR-0026).

The ``/goals/ws`` endpoint broadcasts a snapshot of every tracked goal whenever
any goal's state changes and a ``done`` frame once all goals are terminal. We
inject a fake Supervisor into the gateway module so the test runs offline (no
real DeveloperPlatform / network), seed it with a terminal goal, and assert the
stream surfaces it and emits the terminal ``done`` frame.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from aios.gateway.main import app
from aios.supervisor import Goal, GoalStatus


def test_goals_ws_route_registered() -> None:
    paths = {route.path for route in app.routes}
    assert "/goals/ws" in paths


def test_goals_ws_emits_snapshot_then_done(monkeypatch) -> None:
    import aios.gateway.main as m

    # Build an offline Supervisor and seed it with one terminal goal.
    from aios.supervisor import Supervisor

    class _FakePlatform:
        def resolve(self, capability):
            class _R:
                provider_kind = "native"
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

        async def execute_skill(self, *args, **kwargs):
            from aios.skills.base import SkillResult, SkillStatus

            return SkillResult(status=SkillStatus.SUCCESS, data={})

    sup = Supervisor(_FakePlatform())
    goal = Goal(objective="summarize the homepage", status=GoalStatus.COMPLETED)
    sup._goals[goal.goal_id] = goal
    monkeypatch.setattr(m, "_supervisor", sup)

    client = TestClient(app)
    with client.websocket_connect("/goals/ws") as ws:
        # Read frames until we see the terminal done marker (the stream may
        # emit the snapshot more than once before settling).
        seen_ids: set[str] = set()
        done = False
        for _ in range(10):
            msg = ws.receive_json()
            if msg["type"] == "done":
                done = True
                break
            assert msg["type"] == "snapshot"
            seen_ids |= {g["goal_id"] for g in msg["goals"]}
        assert goal.goal_id in seen_ids
        assert done, "global stream never emitted a done frame"
