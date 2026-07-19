"""Tests for the Supervisor goals API wiring on the gateway (M5.1).

The gateway's FastAPI app is imported to verify the goal-management routes are
registered and reachable. Live request execution is covered end-to-end via the
Supervisor unit tests (``tests/test_supervisor.py``); the gateway simply adapts
the shared Supervisor, so we assert the wiring here without standing up a server.
"""

from __future__ import annotations

from aios.gateway.main import app, get_supervisor


def _paths() -> set[str]:
    return {route.path for route in app.routes}


def test_goals_routes_registered() -> None:
    paths = _paths()
    assert "/goals" in paths
    assert "/goals/{goal_id}" in paths
    assert "/goals/{goal_id}/pause" in paths
    assert "/goals/{goal_id}/resume" in paths
    assert "/goals/{goal_id}/cancel" in paths
    assert "/goals/{goal_id}/events" in paths


def test_get_supervisor_shares_platform_with_app() -> None:
    # Importing the gateway should not raise, and the supervisor should be
    # composable over the shared DeveloperPlatform.
    sup = get_supervisor()
    assert sup.platform is not None
