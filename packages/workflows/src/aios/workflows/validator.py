"""WorkflowValidator — Static validation of workflow definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aios.workflows.base import Workflow


class ValidationError:
    """A single validation problem.

    Attributes:
        severity: 'error' prevents execution; 'warning' is advisory.
        message: Human-readable description.
        step_id: Related step ID, if applicable.
    """

    def __init__(
        self, message: str, *, severity: str = "error",
        step_id: str | None = None,
    ) -> None:
        self.severity = severity
        self.message = message
        self.step_id = step_id

    def __repr__(self) -> str:
        loc = f" step={self.step_id!r}" if self.step_id else ""
        return f"ValidationError({self.severity}{loc}: {self.message})"


@dataclass
class ValidationResult:
    """Result of validating a workflow.

    Attributes:
        errors: List of validation errors found.
    """

    errors: list[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if there are no errors (warnings are OK)."""
        return not any(e.severity == "error" for e in self.errors)

    @property
    def error_count(self) -> int:
        """Number of errors (not warnings)."""
        return sum(1 for e in self.errors if e.severity == "error")

    @property
    def warning_count(self) -> int:
        """Number of warnings."""
        return sum(1 for e in self.errors if e.severity == "warning")


class WorkflowValidator:
    """Validate workflow structure before execution.

    Checks performed:
    - Non-empty ID and name
    - Non-empty steps list
    - No duplicate step IDs
    - All dependencies reference existing steps
    - No circular dependencies
    - Each step has a non-empty type string
    """

    def validate(self, workflow: Workflow) -> ValidationResult:
        """Run all validation checks on a workflow and return the result."""
        result = ValidationResult()
        self._check_basics(workflow, result)
        self._check_duplicate_ids(workflow, result)
        self._check_dependencies_exist(workflow, result)
        self._check_no_cycles(workflow, result)
        self._check_step_types(workflow, result)
        return result

    def _check_basics(self, wf: Workflow, result: ValidationResult) -> None:
        if not wf.id:
            result.errors.append(ValidationError("Workflow ID cannot be empty"))
        if not wf.name:
            result.errors.append(ValidationError("Workflow name cannot be empty"))
        if not wf.steps:
            result.errors.append(ValidationError("Workflow must have at least one step"))

    def _check_duplicate_ids(self, wf: Workflow, result: ValidationResult) -> None:
        seen: set[str] = set()
        for step in wf.steps:
            if step.id in seen:
                result.errors.append(
                    ValidationError(f"Duplicate step ID: {step.id}", step_id=step.id)
                )
            seen.add(step.id)

    def _check_dependencies_exist(self, wf: Workflow, result: ValidationResult) -> None:
        step_ids = {s.id for s in wf.steps}
        for step in wf.steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    result.errors.append(
                        ValidationError(
                            f"Step '{step.id}' depends on non-existent step '{dep}'",
                            step_id=step.id,
                        )
                    )

    def _check_no_cycles(self, wf: Workflow, result: ValidationResult) -> None:
        """Detect cycles using DFS topological sort."""
        step_ids = {s.id for s in wf.steps}
        graph: dict[str, list[str]] = {s.id: [] for s in wf.steps}
        for step in wf.steps:
            for dep in step.dependencies:
                if dep in step_ids:
                    graph[step.id].append(dep)

        WHITE, GRAY, BLACK = 0, 1, 2  # noqa: N806
        color: dict[str, int] = dict.fromkeys(graph, WHITE)

        def dfs(node: str) -> bool:
            """Returns True if a cycle is found."""
            color[node] = GRAY
            for neighbor in graph.get(node, []):
                if color[neighbor] == GRAY:
                    return True  # Cycle detected
                if color[neighbor] == WHITE and dfs(neighbor):
                    return True
            color[node] = BLACK
            return False

        for sid in graph:
            if color[sid] == WHITE and dfs(sid):
                    result.errors.append(
                        ValidationError(
                            f"Circular dependency detected involving step '{sid}'"
                        )
                    )
                    break  # One error for the whole cycle is enough

    def _check_step_types(self, wf: Workflow, result: ValidationResult) -> None:
        known_types = {"agent_call", "tool_call", "condition", "approval", "parallel"}
        for step in wf.steps:
            if not step.type:
                result.errors.append(
                    ValidationError("Step type cannot be empty", step_id=step.id)
                )
            elif step.type not in known_types:
                result.errors.append(
                    ValidationError(
                        f"Unknown step type '{step.type}' "
                        f"(known: {', '.join(sorted(known_types))})",
                        severity="warning",
                        step_id=step.id,
                    )
                )
