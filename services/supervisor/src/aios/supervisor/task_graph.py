"""M6 canonical task graph — the execution contract for autonomous goals.

AIOS never executes free-form planner text. The planner emits a typed DAG
(:class:`TaskGraph`) that is validated before any skill runs. Each :class:`Task`
is bound to a logical *capability* (resolved natively-first by the
:class:`~aios.platform.CapabilityResolver`), not a concrete skill name, so the
executor stays provider-agnostic.

Task schema (per the M6 design):
    id               unique string
    capability       logical capability id (e.g. "browser.search", "notes.write")
    action           skill-specific action verb (e.g. "search", "write")
    inputs           arguments passed to the skill
    depends_on       ids of tasks that must complete first
    expected_output  short description for observability / reflection (M6.1)

The graph is intentionally serialisable (dataclasses → dict) so it can be
persisted with the goal and survive daemon restarts (M5.3).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    """A single executable unit in an autonomous goal.

    ``capability`` is the contract; the executor resolves it to a provider at
    run time. ``action`` and ``inputs`` are passed straight to the resolved
    skill's ``run``.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    capability: str = ""
    action: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    expected_output: str = ""
    retry: dict[str, Any] | None = None
    reflect: bool = True

    def __post_init__(self) -> None:
        if not self.id:
            self.id = uuid.uuid4().hex[:12]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "capability": self.capability,
            "action": self.action,
            "inputs": self.inputs,
            "depends_on": list(self.depends_on),
            "expected_output": self.expected_output,
            "retry": self.retry,
            "reflect": self.reflect,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        return cls(
            id=data.get("id", ""),
            capability=data.get("capability", ""),
            action=data.get("action", ""),
            inputs=data.get("inputs", {}) or {},
            depends_on=data.get("depends_on", []) or [],
            expected_output=data.get("expected_output", ""),
            retry=data.get("retry"),
            reflect=bool(data.get("reflect", True)),
        )


@dataclass
class TaskGraph:
    """A validated DAG of :class:`Task` objects plus goal metadata."""

    goal: str = ""
    tasks: list[Task] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ids(self) -> set[str]:
        return {t.id for t in self.tasks}

    def get(self, task_id: str) -> Task | None:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "tasks": [t.to_dict() for t in self.tasks],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskGraph:
        return cls(
            goal=data.get("goal", ""),
            tasks=[Task.from_dict(t) for t in data.get("tasks", [])],
            metadata=data.get("metadata", {}) or {},
        )


def validate_task_graph(graph: TaskGraph) -> list[str]:
    """Return a list of validation errors (empty list == valid).

    Guards the execution contract: every task needs a capability, ids are
    unique, dependencies reference known tasks, and there are no cycles.
    """
    errors: list[str] = []

    ids: dict[str, int] = {}
    for i, task in enumerate(graph.tasks):
        if not task.capability:
            errors.append(f"task '{task.id}' at index {i} has no capability")
        if not task.id:
            errors.append(f"task at index {i} has no id")
            continue
        ids[task.id] = ids.get(task.id, 0) + 1

    for dup_id, count in ids.items():
        if count > 1:
            errors.append(f"duplicate task id: '{dup_id}'")

    known = set(ids)
    errors.extend(
        f"task '{task.id}' depends on unknown task '{dep}'"
        for task in graph.tasks
        for dep in task.depends_on
        if dep not in known
    )

    # Cycle detection (DFS).
    visiting: set[str] = set()
    done: set[str] = set()

    def _visit(node_id: str, path: list[str]) -> None:
        if node_id in done:
            return
        if node_id in visiting:
            errors.append(
                f"cycle detected: {' -> '.join([*path, node_id])}"
            )
            return
        visiting.add(node_id)
        node = graph.get(node_id)
        if node is not None:
            for dep in node.depends_on:
                _visit(dep, [*path, node_id])
        visiting.discard(node_id)
        done.add(node_id)

    for task in graph.tasks:
        _visit(task.id, [])

    return errors
