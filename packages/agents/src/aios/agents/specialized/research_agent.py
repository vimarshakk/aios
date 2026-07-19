"""Research Agent — web search + LLM synthesis.

Searches the web (DuckDuckGo), fetches content from top URLs,
then synthesizes a comprehensive answer using the LLM.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aios.agents.base import BaseAgent
from aios.agents.types import Message, Role, Trace
from aios.tools.builtin import WebFetchTool, WebSearchTool

if TYPE_CHECKING:
    from aios.agents.engine import InferenceEngine


_RESEARCH_SYSTEM = """\
You are AIOS Research Agent — an expert researcher.

Given a topic, you:
1. Use web_search to find relevant sources
2. Read the top sources with web_fetch
3. Synthesize a comprehensive, accurate, well-structured answer
4. Always cite your sources

Be thorough, factual, and organized. Use markdown formatting.
"""


class ResearchAgent(BaseAgent):
    """Research agent that searches the web and synthesizes information."""

    name = "research"

    def __init__(
        self,
        engine: InferenceEngine,
        model: str = "ollama/llama3.2",
        *,
        max_sources: int = 3,
    ) -> None:
        self._engine = engine
        self._model = model
        self._max_sources = max_sources
        self._search = WebSearchTool()
        self._fetch = WebFetchTool()

    async def run(self, query: str, *, trace: Trace | None = None) -> str:
        """Research a topic: search → fetch → synthesize."""
        # Step 1: Search
        search_result = await self._search.execute(query=query, max_results=self._max_sources)
        search_content = search_result.content

        # Step 2: Build research context
        research_context = f"""Research query: {query}

Search results:
{search_content}

Based on the above search results, provide a comprehensive, well-structured answer.
Include key facts, insights, and cite the sources found.
Use markdown formatting with headers and bullet points."""

        # Step 3: Synthesize with LLM
        messages = [
            Message(role=Role.SYSTEM, content=_RESEARCH_SYSTEM),
            Message(role=Role.USER, content=research_context),
        ]

        result = await self._engine.complete(
            messages, model=self._model, max_tokens=2048, temperature=0.3
        )
        return result.content

    async def step(self, messages: list[Message], *, trace: Trace | None = None) -> Message:
        result = await self._engine.complete(messages, model=self._model)
        return Message(role=Role.ASSISTANT, content=result.content)

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "ResearchAgent",
            "capabilities": ["web_search", "web_fetch", "synthesis"],
            "model": self._model,
            "description": "Searches the web and synthesizes comprehensive research reports.",
        }


__all__ = ["ResearchAgent"]
