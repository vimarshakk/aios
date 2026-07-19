"""Agent pool — capability-aware agent management for multi-agent execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aios.agents.base import BaseAgent


@dataclass
class AgentEntry:
    """A registered agent with its capabilities and health status."""

    name: str
    agent: BaseAgent
    capabilities: set[str] = field(default_factory=set)
    priority: int = 0  # lower = preferred when capabilities match equally
    healthy: bool = True


class AgentPool:
    """Manages a pool of agents with capability-based selection.

    Agents register with a set of capabilities. When a subtask requires
    specific capabilities, the pool selects the best-matching healthy agent.
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentEntry] = {}

    def register(
        self,
        name: str,
        agent: BaseAgent,
        capabilities: set[str] | None = None,
        priority: int = 0,
    ) -> None:
        """Register an agent with optional capabilities."""
        self._agents[name] = AgentEntry(
            name=name,
            agent=agent,
            capabilities=capabilities or set(),
            priority=priority,
            healthy=True,
        )

    def deregister(self, name: str) -> bool:
        """Remove an agent from the pool. Returns True if found."""
        if name in self._agents:
            del self._agents[name]
            return True
        return False

    def get(self, name: str) -> AgentEntry | None:
        """Get an agent entry by name."""
        return self._agents.get(name)

    def select(self, required_capabilities: set[str]) -> AgentEntry | None:
        """Select the best healthy agent matching required capabilities.

        Selection criteria (in order):
        1. Must be healthy
        2. Must have ALL required capabilities (or pool is empty-required)
        3. Lowest priority number wins
        4. Fewest total capabilities wins (most specialized)
        """
        candidates: list[AgentEntry] = []

        for entry in self._agents.values():
            if not entry.healthy:
                continue
            if required_capabilities and not required_capabilities.issubset(entry.capabilities):
                continue
            candidates.append(entry)

        if not candidates:
            return None

        # Sort: lowest priority first, then fewest capabilities
        candidates.sort(key=lambda e: (e.priority, len(e.capabilities)))
        return candidates[0]

    def select_all(self, required_capabilities: set[str]) -> list[AgentEntry]:
        """Select all healthy agents matching required capabilities."""
        candidates: list[AgentEntry] = []

        for entry in self._agents.values():
            if not entry.healthy:
                continue
            if required_capabilities and not required_capabilities.issubset(entry.capabilities):
                continue
            candidates.append(entry)

        candidates.sort(key=lambda e: (e.priority, len(e.capabilities)))
        return candidates

    def list_healthy(self) -> list[AgentEntry]:
        """Return all healthy agents sorted by priority."""
        return sorted(
            [e for e in self._agents.values() if e.healthy],
            key=lambda e: (e.priority, e.name),
        )

    def list_all(self) -> list[AgentEntry]:
        """Return all agents sorted by priority."""
        return sorted(self._agents.values(), key=lambda e: (e.priority, e.name))

    def mark_unhealthy(self, name: str) -> bool:
        """Mark an agent as unhealthy. Returns True if found."""
        entry = self._agents.get(name)
        if entry:
            entry.healthy = False
            return True
        return False

    def mark_healthy(self, name: str) -> bool:
        """Mark an agent as healthy. Returns True if found."""
        entry = self._agents.get(name)
        if entry:
            entry.healthy = True
            return True
        return False

    def capabilities_summary(self) -> dict[str, set[str]]:
        """Return {agent_name: capabilities} for all healthy agents."""
        return {
            name: entry.capabilities
            for name, entry in self._agents.items()
            if entry.healthy
        }

    def all_capabilities(self) -> set[str]:
        """Return the union of all healthy agent capabilities."""
        caps: set[str] = set()
        for entry in self._agents.values():
            if entry.healthy:
                caps.update(entry.capabilities)
        return caps

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, name: str) -> bool:
        return name in self._agents
