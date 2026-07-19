"""Tests for aios.platform — runtime composition of M4 packages."""

from __future__ import annotations

import pytest

from aios.agents.base import BaseAgent
from aios.agents.types import Message, Role
from aios.platform import DeveloperPlatform


class _StubAgent(BaseAgent):
    """Minimal agent for platform registration tests."""

    name = "stub"

    def __init__(self, model: str = "stub") -> None:
        self._model = model

    async def run(self, query: str, *, trace=None) -> str:
        return f"stub: {query}"

    async def step(self, messages, *, trace=None):
        return Message(role=Role.ASSISTANT, content="stub-step")


@pytest.fixture
def platform() -> DeveloperPlatform:
    pf = DeveloperPlatform(
        encryptor_password="test-master",  # noqa: S106  (test fixture)
        granted_permissions=["FILESYSTEM_READ", "PROCESS_EXEC"],
    )
    pf.bootstrap()
    return pf


class TestAgentRegistration:
    def test_registers_and_indexes_catalog(self, platform) -> None:
        reg = platform.register_agent(
            "research",
            _StubAgent(),
            capability_ids=["browser.navigate", "filesystem.read", "network.http"],
        )
        assert reg.name == "research"
        # catalog-backed capabilities resolved to nodes
        cap_names = {c.name for c in reg.capabilities}
        assert "browser.navigate" in cap_names
        assert platform.list_agent_capabilities("research") == [
            "browser.navigate",
            "filesystem.read",
            "network.http",
        ]
        assert "research" in platform.orchestrator.list_agents()

    def test_unknown_capability_accepted_but_not_indexed(self, platform) -> None:
        reg = platform.register_agent(
            "x", _StubAgent(), capability_ids=["does-not-exist"]
        )
        assert reg.capabilities == []
        assert reg.catalog_size == len(platform.catalog.all())


class TestAuthorization:
    def test_sensitive_permission_requires_approval(self, platform) -> None:
        decision = platform.authorize(
            capabilities=["filesystem.delete"],
            permissions=["fs.delete"],
        )
        assert decision.requires_approval
        assert not decision.denied

    def test_forbidden_permission_denied(self, platform) -> None:
        decision = platform.authorize(permissions=["filesystem.format"])
        assert decision.denied
        assert decision.level.value == "deny"


class TestSkillsAndPlanning:
    def test_plan_returns_skills(self, platform) -> None:
        plan = platform.plan("review this code", capabilities=["filesystem.read"])
        assert not plan.empty
        assert "code-review" in plan.skills

    async def test_execute_builtin_skill(self, platform) -> None:
        result = await platform.execute_skill(
            "code-review", inputs={"diff": "def f(x): return x"}
        )
        assert result.status.value == "success"
        assert len(platform.execution_history) == 1


class TestWorkspaces:
    def test_create_and_use_workspace(self, platform) -> None:
        ws = platform.create_workspace("ws1", skill_names=["code-review"])
        assert ws.id == "ws1"
        assert ws.has_skill("code-review")
        platform.secrets.put("GH_TOKEN", "secret-value")
        ws.put_scoped_secret("GH_TOKEN", "scoped-value")
        assert ws.scoped_secret("GH_TOKEN") == "scoped-value"
