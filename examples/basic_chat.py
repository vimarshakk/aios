"""Basic chat example using AIOS SDK."""

import asyncio

from aios.sdk import AiosClient


async def main():
    """Run a basic chat example."""
    client = AiosClient("http://localhost:8080")

    # Simple chat
    response = client.chat("Hello, what can you do?")
    print("Response:", response)

    # Chat with session
    response1 = client.chat("My name is Alice", session_id="demo_session")
    print("Response 1:", response1)

    response2 = client.chat("What's my name?", session_id="demo_session")
    print("Response 2:", response2)


if __name__ == "__main__":
    asyncio.run(main())
