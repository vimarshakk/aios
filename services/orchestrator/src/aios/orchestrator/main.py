"""AIOS Orchestrator — central query router and session manager.

Extracted from OpenJarvis orchestrator patterns (Apache 2.0).
Routes incoming queries to the appropriate agent, manages conversation state,
chains tool calls, and coordinates memory retrieval.

M2.1: Adds multi-agent routing mode — decompose, execute in parallel, aggregate.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aios.agents import Conversation, EventType, Message, Role, get_event_bus
from aios.agents.aggregator import ResultAggregator
from aios.agents.multi_executor import MultiAgentExecutor
from aios.agents.pool import AgentPool
from aios.agents.task import TaskDecomposer
from aios.agents.types import ToolResult

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from aios.agents.base import BaseAgent


@dataclass
class Session:
    """A user session with conversation history."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    conversation: Conversation = field(default_factory=Conversation)
    metadata: dict[str, Any] = field(default_factory=dict)
    agent_name: str = "default"


class Orchestrator:
    """Central orchestrator that routes queries to agents.

    Supports two modes:
    - single (default): route to one named agent
    - multi: decompose → pool select → parallel execute → aggregate
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._agents: dict[str, BaseAgent] = {}
        self._tool_fns: dict[str, Callable[..., Coroutine[Any, Any, ToolResult]]] = {}
        self._pool = AgentPool()
        self._decomposer = TaskDecomposer()
        self._aggregator = ResultAggregator()

    def register_agent(
        self,
        name: str,
        agent: BaseAgent,
        capabilities: set[str] | None = None,
        priority: int = 0,
    ) -> None:
        """Register an agent. If capabilities are provided, also registers in the pool."""
        self._agents[name] = agent
        if capabilities is not None:
            self._pool.register(name, agent, capabilities, priority)

    def register_tool(self, name: str, fn: Callable[..., Coroutine[Any, Any, ToolResult]]) -> None:
        self._tool_fns[name] = fn

    def get_or_create_session(self, session_id: str | None = None) -> Session:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        session = Session(id=session_id or uuid.uuid4().hex[:12])
        self._sessions[session.id] = session
        bus = get_event_bus()
        bus.publish(EventType.SESSION_START, {"session_id": session.id})
        return session

    async def route(
        self,
        query: str,
        *,
        session_id: str | None = None,
        agent_name: str | None = None,
        mode: str = "single",
    ) -> str:
        """Route a query to agents.

        mode="single": route to one named agent (original behavior).
        mode="multi": decompose, execute across pool, aggregate.
        """
        if mode == "multi":
            return await self._route_multi(query, session_id=session_id)
        return await self._route_single(query, session_id=session_id, agent_name=agent_name)

    async def _route_single(
        self,
        query: str,
        *,
        session_id: str | None = None,
        agent_name: str | None = None,
    ) -> str:
        """Route a query to a single agent (original behavior)."""
        bus = get_event_bus()
        session = self.get_or_create_session(session_id)

        if agent_name:
            session.agent_name = agent_name

        agent = self._agents.get(session.agent_name)
        if not agent:
            return f"No agent registered for '{session.agent_name}'"

        bus.publish(EventType.AGENT_TURN_START, {
            "session_id": session.id,
            "agent": session.agent_name,
            "query": query,
        })

        session.conversation.add(Message(role=Role.USER, content=query))
        response = await agent.run(query)
        session.conversation.add(Message(role=Role.ASSISTANT, content=response))

        bus.publish(EventType.AGENT_TURN_END, {
            "session_id": session.id,
            "agent": session.agent_name,
            "response_length": len(response),
        })
        return response

    async def _route_multi(
        self,
        query: str,
        *,
        session_id: str | None = None,
    ) -> str:
        """Multi-agent routing: decompose → execute → aggregate."""
        bus = get_event_bus()
        session = self.get_or_create_session(session_id)

        bus.publish(EventType.AGENT_TURN_START, {
            "session_id": session.id,
            "agent": "multi",
            "query": query,
        })

        session.conversation.add(Message(role=Role.USER, content=query))

        # 1. Decompose
        available_caps = self._pool.all_capabilities()
        subtasks = self._decomposer.decompose(query, available_caps)

        bus.publish(EventType.WORKFLOW_START, {
            "session_id": session.id,
            "subtasks": len(subtasks),
        })

        # 2. Execute
        executor = MultiAgentExecutor(self._pool)
        results = await executor.execute(subtasks)

        # 3. Aggregate
        response = self._aggregator.aggregate(results, query)

        session.conversation.add(Message(role=Role.ASSISTANT, content=response))

        bus.publish(EventType.WORKFLOW_END, {
            "session_id": session.id,
            "results": len(results),
        })

        bus.publish(EventType.AGENT_TURN_END, {
            "session_id": session.id,
            "agent": "multi",
            "response_length": len(response),
        })
        return response

    @property
    def pool(self) -> AgentPool:
        """Access the agent pool for direct management."""
        return self._pool

    async def call_tool(self, name: str, **kwargs: Any) -> ToolResult:
        fn = self._tool_fns.get(name)
        if not fn:
            return ToolResult(
                tool_name=name,
                content=f"Tool '{name}' not registered",
                success=False,
            )
        return await fn(**kwargs)

    def list_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())


def run() -> None:
    """Entry point for the orchestrator service."""
    orchestrator = Orchestrator()
    print(f"AIOS Orchestrator started. Agents: {orchestrator.list_agents()}")


__all__ = ["Orchestrator", "Session", "run"]
