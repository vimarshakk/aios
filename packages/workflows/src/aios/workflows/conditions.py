"""Conditional branching — ConditionStep evaluates predicates and routes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aios.workflows.base import WorkflowStep

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class Condition:
    """A single branch condition.

    Attributes:
        label: Human-readable label for this branch.
        predicate: Callable that receives results and returns True if this branch applies.
        target_step_id: The step ID to jump to if the condition is true.
    """

    label: str
    predicate: Callable[[dict[str, Any]], bool] | None = None
    target_step_id: str | None = None


@dataclass
class ConditionResult:
    """Result of evaluating a ConditionStep.

    Attributes:
        matched: The condition that matched (or None if default was used).
        target_step_id: The step to execute next.
        evaluated: Dict of condition label → bool showing all evaluations.
    """

    matched: Condition | None
    target_step_id: str | None
    evaluated: dict[str, bool] = field(default_factory=dict)


@dataclass
class ConditionStep(WorkflowStep):
    """A workflow step that evaluates conditions and selects the next step.

    Attributes:
        conditions: List of Condition objects to evaluate in order.
        default_step_id: Step to run if no condition matches.
    """

    conditions: list[Condition] = field(default_factory=list)
    default_step_id: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.type = "condition"

    async def evaluate(self, results: dict[str, Any]) -> ConditionResult:
        """Evaluate conditions in order and return the first match.

        Falls back to default_step_id if no condition matches.
        """
        evaluated: dict[str, bool] = {}
        for cond in self.conditions:
            if cond.predicate is not None:
                matched = cond.predicate(results)
            else:
                matched = results.get(cond.label) is not None
            evaluated[cond.label] = matched
            if matched:
                return ConditionResult(
                    matched=cond,
                    target_step_id=cond.target_step_id,
                    evaluated=evaluated,
                )
        return ConditionResult(
            matched=None,
            target_step_id=self.default_step_id,
            evaluated=evaluated,
        )


async def default_condition_evaluator(
    step: ConditionStep,
    results: dict[str, Any],
) -> str | None:
    """Evaluate a ConditionStep and return the target step ID, or None for default."""
    result = await step.evaluate(results)
    return result.target_step_id
