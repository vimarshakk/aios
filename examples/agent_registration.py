"""Agent registration and multi-agent orchestration example."""

import asyncio

from aios.agents import ReActAgent
from aios.orchestrator import Orchestrator


async def main():
    """Demonstrate agent registration and routing."""
    orchestrator = Orchestrator()

    # Create agents with different capabilities
    coder = ReActAgent(
        name="coder",
        model="gpt-4",
        system_prompt="You are an expert Python programmer.",
    )

    researcher = ReActAgent(
        name="researcher",
        model="gpt-4",
        system_prompt="You are a research specialist.",
    )

    # Register agents
    orchestrator.register_agent("coder", coder, capabilities={"coding", "python"})
    orchestrator.register_agent("researcher", researcher, capabilities={"research", "analysis"})

    # Single agent routing
    response = await orchestrator.route(
        "Write a Python function to calculate factorial",
        agent_name="coder",
    )
    print("Coder response:", response)

    # Multi-agent routing (decompose → execute → aggregate)
    response = await orchestrator.route(
        "Research Python async patterns and write a brief summary",
        mode="multi",
    )
    print("Multi-agent response:", response)


if __name__ == "__main__":
    asyncio.run(main())
