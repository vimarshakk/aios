"""Memory system usage example."""

import asyncio

from aios.memory import Memory


async def main():
    """Demonstrate memory storage and retrieval."""
    memory = Memory()

    # Store user preferences
    await memory.store(
        "user_preference",
        "I prefer dark mode in all applications",
        metadata={"category": "ui", "user": "alice"},
    )

    await memory.store(
        "user_preference",
        "My timezone is UTC+5:30 (India)",
        metadata={"category": "location", "user": "alice"},
    )

    # Store some knowledge
    await memory.store(
        "knowledge",
        "Python 3.12 introduced improved error messages and perf improvements",
        metadata={"category": "python"},
    )

    # Search for relevant information
    results = await memory.search("What are the user's UI preferences?")
    print("UI preferences:", results)

    results = await memory.search("Tell me about Python 3.12")
    print("Python info:", results)


if __name__ == "__main__":
    asyncio.run(main())
