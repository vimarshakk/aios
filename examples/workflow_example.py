"""Workflow engine example."""

import asyncio

from aios.workflows import (
    Condition,
    ConditionStep,
    RetryPolicy,
    Workflow,
    WorkflowStep,
)


async def main():
    """Demonstrate workflow creation and execution."""

    # Simple linear workflow
    workflow = Workflow(
        name="research_and_write",
        description="Research a topic and write an article",
        steps=[
            WorkflowStep(
                name="research",
                prompt="Research the topic: {topic}",
            ),
            WorkflowStep(
                name="outline",
                prompt="Create an outline based on: {research_result}",
            ),
            WorkflowStep(
                name="write",
                prompt="Write an article using this outline: {outline_result}",
            ),
            WorkflowStep(
                name="review",
                prompt="Review and improve: {write_result}",
            ),
        ],
    )

    print("Workflow:", workflow.name)
    print("Steps:", [step.name for step in workflow.steps])


if __name__ == "__main__":
    asyncio.run(main())
