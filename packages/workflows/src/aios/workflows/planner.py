"""WorkflowPlanner — LLM-based task decomposition into workflow steps."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any

from aios.workflows.base import Workflow, WorkflowStep

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class WorkflowPlanner:
    """Use an LLM to decompose a high-level task into workflow steps.

    The planner takes a task description and available tools, asks the LLM
    to produce a structured plan, and returns a Workflow object.

    Attributes:
        llm_fn: Async callable that takes a prompt string and returns an LLM response string.
        max_steps: Maximum number of steps the planner should generate.
    """

    def __init__(
        self,
        llm_fn: Callable[[str], Awaitable[str]] | None = None,
        max_steps: int = 20,
    ) -> None:
        self.llm_fn = llm_fn
        self.max_steps = max_steps

    async def plan(
        self,
        task: str,
        available_tools: list[dict[str, Any]] | None = None,
        *,
        workflow_name: str | None = None,
    ) -> Workflow:
        """Decompose a task into a Workflow with ordered steps.

        Args:
            task: High-level task description.
            available_tools: List of tool specs the planner can use.
                Each dict should have at least "name" and "description".
            workflow_name: Optional name for the workflow.

        Returns:
            A Workflow with steps and dependencies resolved.
        """
        if self.llm_fn is not None:
            return await self._plan_with_llm(task, available_tools, workflow_name)
        return self._plan_deterministic(task, available_tools, workflow_name)

    async def _plan_with_llm(
        self,
        task: str,
        available_tools: list[dict[str, Any]] | None,
        workflow_name: str | None,
    ) -> Workflow:
        """Use the LLM to generate a workflow plan."""
        prompt = self._build_prompt(task, available_tools)
        response = await self.llm_fn(prompt)  # type: ignore[misc]
        steps = self._parse_llm_response(response)

        return Workflow(
            id=uuid.uuid4().hex[:12],
            name=workflow_name or task[:50],
            steps=steps,
            metadata={"source": "llm_planner", "task": task},
        )

    def _plan_deterministic(
        self,
        task: str,
        available_tools: list[dict[str, Any]] | None,
        workflow_name: str | None,
    ) -> Workflow:
        """Create a simple single-step workflow when no LLM is available."""
        tools = available_tools or []
        config: dict[str, Any] = {"task": task}
        if tools:
            config["tools"] = [t.get("name", "unknown") for t in tools]

        step = WorkflowStep(
            id=uuid.uuid4().hex[:12],
            type="tool_call",
            config=config,
        )

        return Workflow(
            id=uuid.uuid4().hex[:12],
            name=workflow_name or task[:50],
            steps=[step],
            metadata={"source": "deterministic_planner", "task": task},
        )

    def _build_prompt(
        self, task: str, available_tools: list[dict[str, Any]] | None
    ) -> str:
        """Build the LLM prompt for task decomposition."""
        tools_section = ""
        if available_tools:
            tool_list = "\n".join(
                f"- {t.get('name', '?')}: {t.get('description', 'no description')}"
                for t in available_tools
            )
            tools_section = f"\n\nAvailable tools:\n{tool_list}"

        return f"""You are a workflow planner. Break the following task into executable steps.

Task: {task}
{tools_section}

Return a JSON array of steps. Each step is an object with:
- "id": unique string identifier
- "type": one of "agent_call", "tool_call", "condition", "approval", "parallel"
- "config": dict with step-specific configuration
- "dependencies": list of step IDs that must complete before this step

Return ONLY the JSON array, no other text. Max {self.max_steps} steps.

Example:
[
  {{"id": "step1", "type": "tool_call",
   "config": {{"tool": "search"}}, "dependencies": []}},
  {{"id": "step2", "type": "agent_call",
   "config": {{"prompt": "summarize"}},
   "dependencies": ["step1"]}}
]"""

    def _parse_llm_response(self, response: str) -> list[WorkflowStep]:
        """Parse the LLM response into WorkflowStep objects."""
        # Strip markdown fences if present
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [
                ln for ln in lines
                if not ln.strip().startswith("```")
            ]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Fallback: return a single step with the raw response
            return [
                WorkflowStep(
                    id=uuid.uuid4().hex[:12],
                    type="tool_call",
                    config={"raw_response": text},
                )
            ]

        if not isinstance(data, list):
            data = [data]

        return [
            WorkflowStep(
                id=item.get("id", uuid.uuid4().hex[:12]),
                type=item.get("type", "tool_call"),
                config=item.get("config", {}),
                dependencies=item.get("dependencies", []),
            )
            for item in data[: self.max_steps]
            if isinstance(item, dict)
        ]
