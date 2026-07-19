"""Tests for the Orchestrator."""

import pytest

from aios.agents.base import BaseAgent
from aios.agents.events import reset_event_bus
from aios.agents.types import Message
from aios.orchestrator.main import Orchestrator, Session


class DummyAgent(BaseAgent):
    """A minimal test agent."""

    def __init__(self, response: str = "Hello"):
        self._response = response

    async def run(self, query: str, **kwargs) -> str:
        return self._response

    async def step(self, messages: list[Message], **kwargs) -> Message:
        return Message(role="assistant", content=self._response)

    def describe(self) -> dict:
        return {"name": "dummy", "description": "A test agent"}


class TestSession:
    def test_construction(self):
        session = Session()
        assert len(session.id) == 12
        assert session.agent_name == "default"

    def test_custom_id(self):
        session = Session(id="custom-123")
        assert session.id == "custom-123"


class TestOrchestrator:
    def test_construction(self):
        orch = Orchestrator()
        assert orch.list_agents() == []
        assert orch.list_sessions() == []

    def test_register_agent(self):
        orch = Orchestrator()
        orch.register_agent("test", DummyAgent())
        assert "test" in orch.list_agents()

    def test_get_or_create_session(self):
        orch = Orchestrator()
        session = orch.get_or_create_session("s1")
        assert session.id == "s1"
        assert len(orch.list_sessions()) == 1

    def test_existing_session_reused(self):
        orch = Orchestrator()
        s1 = orch.get_or_create_session("s1")
        s2 = orch.get_or_create_session("s1")
        assert s1 is s2
        assert len(orch.list_sessions()) == 1

    def test_new_session_without_id(self):
        orch = Orchestrator()
        session = orch.get_or_create_session()
        assert len(session.id) == 12

    @pytest.mark.asyncio
    async def test_route_to_agent(self):
        reset_event_bus()
        orch = Orchestrator()
        orch.register_agent("dummy", DummyAgent(response="Hi there!"))
        response = await orch.route("hello", agent_name="dummy")
        assert response == "Hi there!"

    @pytest.mark.asyncio
    async def test_route_no_agent(self):
        orch = Orchestrator()
        response = await orch.route("hello", agent_name="nonexistent")
        assert "No agent registered" in response

    @pytest.mark.asyncio
    async def test_route_updates_conversation(self):
        reset_event_bus()
        orch = Orchestrator()
        orch.register_agent("dummy", DummyAgent(response="Hi!"))
        await orch.route("hello", agent_name="dummy")
        session = orch.list_sessions()[0]
        assert len(session.conversation.messages) == 2
        assert session.conversation.messages[0].content == "hello"
        assert session.conversation.messages[1].content == "Hi!"
