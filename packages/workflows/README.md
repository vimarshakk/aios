# AIOS Workflows Package

The workflows package provides a powerful workflow engine with serial/parallel execution, conditions, approvals, and validation.

## Features

- **Workflow** - Define multi-step workflows
- **WorkflowStep** - Individual steps in a workflow
- **WorkflowExecutor** - Execute workflows with retry and timeout
- **WorkflowPlanner** - AI-powered workflow planning
- **Conditions** - Conditional execution paths
- **Approvals** - Human-in-the-loop approval steps
- **Parallel Execution** - Run steps in parallel
- **Validation** - Workflow structure validation

## Quick Start

```python
from aios.workflows import Workflow, WorkflowStep

# Define a workflow
workflow = Workflow(
    name="research_and_write",
    steps=[
        WorkflowStep(name="research", prompt="Research {topic}"),
        WorkflowStep(name="write", prompt="Write about {research_result}"),
    ]
)

# Execute the workflow
result = await workflow.execute(topic="Python async patterns")
print(result)
```

## Parallel Execution

```python
from aios.workflows import execute_parallel, ParallelGroup

# Run steps in parallel
group = ParallelGroup(
    steps=[
        WorkflowStep(name="step1", prompt="Task 1"),
        WorkflowStep(name="step2", prompt="Task 2"),
        WorkflowStep(name="step3", prompt="Task 3"),
    ]
)

results = await execute_parallel(group)
```

## Conditional Steps

```python
from aios.workflows import Condition, ConditionStep

# Add conditional logic
step = ConditionStep(
    name="check_result",
    condition=Condition(
        field="result.quality",
        operator="gt",
        value=0.8
    ),
    if_true=WorkflowStep(name="proceed", prompt="Continue"),
    if_false=WorkflowStep(name="retry", prompt="Retry with different approach"),
)
```

## Documentation

See the main [README](../../README.md) for more information.
