"""Abstract base classes for tools.

Extracted from OpenJarvis tools/_stubs.py (Apache 2.0).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aios.agents.types import ToolResult


@dataclass
class ToolSpec:
    """JSON-serializable tool description for LLM tool-use APIs."""
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)
    category: str = "general"


class BaseTool(ABC):
    """All tools must implement this interface."""

    spec: ToolSpec
    permissions: tuple[str, ...] = ()

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Run the tool with the given arguments."""
        ...

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.spec.name,
            "description": self.spec.description,
            "category": self.spec.category,
        }


class BaseConnector(ABC):
    """Base class for external data source connectors (Gmail, Slack, etc.)."""

    name: str = "base_connector"

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the external service."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection."""
        ...

    @abstractmethod
    async def query(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Query data from the connector."""
        ...


__all__ = ["BaseConnector", "BaseTool", "ToolSpec"]
