"""Task decomposition — break complex queries into subtasks for multi-agent execution."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Subtask:
    """A unit of work to be executed by a single agent."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    query: str = ""
    required_capabilities: frozenset[str] = field(default_factory=frozenset)
    dependencies: frozenset[str] = field(default_factory=frozenset)
    priority: int = 0  # lower = higher priority
    metadata: dict[str, Any] = field(default_factory=dict)

    def depends_on(self, other: Subtask) -> bool:
        return other.id in self.dependencies

    def is_ready(self, completed: set[str]) -> bool:
        return self.dependencies.issubset(completed)


class TaskDecomposer:
    """Decomposes a user query into subtasks.

    M1 implementation: rule-based decomposition.
    - Single-capability queries → single subtask
    - Multi-sentence queries → one subtask per sentence
    - Queries with explicit separators ("and then", "also", ";") → split
    """

    _SEPARATORS = (" and then ", " also ", "; ", " | ")

    def decompose(
        self,
        query: str,
        available_capabilities: set[str],
    ) -> list[Subtask]:
        """Break a query into subtasks based on available agent capabilities.

        If no capabilities are provided or the query is simple, returns
        a single subtask with all available capabilities.
        """
        if not available_capabilities:
            return [Subtask(query=query, required_capabilities=frozenset())]

        parts = self._split_query(query)

        if len(parts) <= 1:
            return [
                Subtask(
                    query=query,
                    required_capabilities=frozenset(available_capabilities),
                )
            ]

        subtasks: list[Subtask] = []
        for i, part in enumerate(parts):
            caps = self._infer_capabilities(part, available_capabilities)
            subtasks.append(
                Subtask(
                    query=part.strip(),
                    required_capabilities=caps or frozenset(available_capabilities),
                    dependencies=frozenset(),
                    priority=i,
                )
            )
        return subtasks

    def _split_query(self, query: str) -> list[str]:
        """Split query into parts using known separators."""
        text = query.strip()
        for sep in self._SEPARATORS:
            if sep in text.lower():
                parts = [p.strip() for p in text.split(sep) if p.strip()]
                if len(parts) > 1:
                    return parts
        # Fallback: split on newlines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines if len(lines) > 1 else [text]

    def _infer_capabilities(
        self, text: str, available: set[str]
    ) -> frozenset[str]:
        """Best-effort capability matching from text content.

        Returns empty frozenset if no match (caller uses all capabilities).
        """
        text_lower = text.lower()
        matched: set[str] = set()
        for cap in available:
            if cap.lower() in text_lower:
                matched.add(cap)
        return frozenset(matched)


def resolve_execution_order(subtasks: list[Subtask]) -> list[list[Subtask]]:
    """Topological sort of subtasks into parallel layers.

    Returns a list of layers, where each layer contains subtasks that
    can run concurrently. Layers must be executed in order.
    """
    if not subtasks:
        return []

    completed: set[str] = set()
    layers: list[list[Subtask]] = []
    remaining = list(subtasks)

    while remaining:
        ready = [s for s in remaining if s.is_ready(completed)]
        if not ready:
            # Circular dependency — break by executing remaining in order
            ready = remaining[:1]

        layers.append(ready)
        for s in ready:
            completed.add(s.id)
            remaining.remove(s)

    return layers
