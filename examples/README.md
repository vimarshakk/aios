# Examples

This directory contains example code demonstrating how to use AIOS.

## Getting Started

### Basic Chat

```python
from aios.sdk import AiosClient

client = AiosClient("http://localhost:8080")
response = client.chat("Hello, what can you do?")
print(response)
```

### Agent Registration

```python
from aios.orchestrator import Orchestrator
from aios.agents import ReActAgent

orchestrator = Orchestrator()

# Create and register an agent
agent = ReActAgent(
    name="assistant",
    model="gpt-4",
    system_prompt="You are a helpful assistant."
)
orchestrator.register_agent(
    "assistant",
    agent,
    capabilities={"general", "coding"}
)

# Route a query
response = await orchestrator.route("Write a Python function to sort a list")
print(response)
```

### Multi-Agent Orchestration

```python
from aios.orchestrator import Orchestrator

orchestrator = Orchestrator()

# Register agents with different capabilities
orchestrator.register_agent(
    "coder",
    coder_agent,
    capabilities={"coding", "python"}
)
orchestrator.register_agent(
    "researcher",
    researcher_agent,
    capabilities={"search", "analysis"}
)
orchestrator.register_agent(
    "writer",
    writer_agent,
    capabilities={"writing", "editing"}
)

# Multi-agent mode: decompose → execute → aggregate
response = await orchestrator.route(
    "Research Python async patterns, write a tutorial, and review it for errors",
    mode="multi",
)
print(response)
```

### Memory System

```python
from aios.memory import Memory

memory = Memory()

# Store information
await memory.store(
    "user_preference",
    "I prefer dark mode in all applications",
    metadata={"category": "ui"}
)

# Retrieve information
results = await memory.search("What are the user's UI preferences?")
print(results)
```

### Workflow Engine

```python
from aios.workflows import Workflow, WorkflowStep

# Define a workflow
workflow = Workflow(
    name="research_and_write",
    steps=[
        WorkflowStep(
            name="research",
            agent="researcher",
            prompt="Research {topic}"
        ),
        WorkflowStep(
            name="write",
            agent="writer",
            prompt="Write an article based on: {research_result}"
        ),
        WorkflowStep(
            name="review",
            agent="reviewer",
            prompt="Review and edit: {draft}"
        ),
    ]
)

# Execute the workflow
result = await workflow.execute(topic="Python async patterns")
print(result)
```

### Plugin System

```python
from aios.plugins import PluginRuntime

runtime = PluginRuntime()

# Install a plugin
await runtime.install("aios-plugin-web-search", version="^1.0.0")

# Use the plugin
web_search = runtime.get_plugin("aios-plugin-web-search")
results = await web_search.search("AIOS documentation")
```

## Running Examples

1. Start the gateway:
   ```bash
   uv run aios-gateway
   ```

2. Run an example:
   ```bash
   uv run python examples/basic_chat.py
   ```

## More Examples

See the `examples/` directory for more complete examples:

- `basic_chat.py` - Simple chat with an agent
- `agent_registration.py` - Register and use multiple agents
- `memory_usage.py` - Store and retrieve from memory
- `workflow_example.py` - Create and execute workflows
- `plugin_example.py` - Install and use plugins
- `multi_agent.py` - Multi-agent orchestration
