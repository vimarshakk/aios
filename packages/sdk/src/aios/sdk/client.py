"""Python SDK client for AIOS Gateway."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class ChatMessage:
    """A chat message."""
    role: str
    content: str


@dataclass
class ChatResult:
    """Result of a chat interaction."""
    response: str
    agent: str
    session_id: str
    messages: list[ChatMessage] = field(default_factory=list)


class AiosClient:
    """Client for the AIOS Gateway HTTP API.

    Usage:
        client = AiosClient("http://localhost:8080")
        result = await client.chat("What's the weather?")
        await client.close()
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session_id: str | None = None
        self._owned_client = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=self.timeout)

    async def chat(
        self,
        message: str,
        *,
        agent: str | None = None,
        session_id: str | None = None,
    ) -> ChatResult:
        """Send a chat message and return the response."""
        sid = session_id or self._session_id
        payload: dict[str, Any] = {"message": message}
        if agent:
            payload["agent"] = agent
        if sid:
            payload["session_id"] = sid

        resp = await self._http.post(f"{self.base_url}/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

        self._session_id = data.get("session_id", sid)
        return ChatResult(
            response=data["response"],
            agent=data.get("agent", "unknown"),
            session_id=self._session_id or "",
        )

    async def health(self) -> dict[str, Any]:
        """Check gateway health."""
        resp = await self._http.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    async def list_agents(self) -> list[dict[str, Any]]:
        """List registered agents."""
        resp = await self._http.get(f"{self.base_url}/agents")
        resp.raise_for_status()
        return resp.json()

    async def list_tools(self) -> list[dict[str, Any]]:
        """List registered tools."""
        resp = await self._http.get(f"{self.base_url}/tools")
        resp.raise_for_status()
        return resp.json()

    def set_session(self, session_id: str) -> None:
        """Set the session ID for subsequent requests."""
        self._session_id = session_id

    def clear_session(self) -> None:
        """Clear the session ID."""
        self._session_id = None

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._owned_client:
            await self._http.aclose()
