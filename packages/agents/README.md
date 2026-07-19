# AIOS Agents Package

The agents package provides the core agent framework for AIOS.

## Features

- **BaseAgent** - Abstract base class for all agents
- **ReActAgent** - ReAct loop implementation with tool calling
- **EventBus** - Publish-subscribe event system
- **AgentPool** - Multi-agent management and capability-based routing
- **ToolRegistry** - Dynamic tool registration and invocation
- **Permissions** - Role-based access control for agents

## Quick Start

```python
from aios.agents import ReActAgent, EventType, get_event_bus

# Create an agent
agent = ReActAgent(
    name="assistant",
    model="gpt-4",
    system_prompt="You are a helpful assistant.",
)

# Run the agent
response = await agent.run("Hello, what can you do?")
print(response)
```

## Multi-Agent Orchestration

```python
from aios.agents import AgentPool, MultiAgentExecutor

# Create a pool
pool = AgentPool()

# Register agents with capabilities
pool.register("coder", coder_agent, capabilities={"coding", "python"})
pool.register("researcher", researcher_agent, capabilities={"research"})

# Execute multi-agent task
executor = MultiAgentExecutor(pool)
results = await executor.execute(subtasks)
```

## Events

```python
from aios.agents import get_event_bus, EventType

bus = get_event_bus()

# Subscribe to events
def on_agent_start(event):
    print(f"Agent started: {event.data}")

bus.subscribe(EventType.AGENT_TURN_START, on_agent_start)

# Events are published automatically by agents
```

## Documentation

See the main [README](../../README.md) for more information.
