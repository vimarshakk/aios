"""Browser Agent — Playwright-based web automation.

Inspired by OpenHands browser agent patterns.
Navigates, clicks, fills forms, extracts content.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from aios.agents.base import BaseAgent
from aios.agents.types import Message, Role, Trace

if TYPE_CHECKING:
    from aios.agents.engine import InferenceEngine


_BROWSER_SYSTEM = """\
You are AIOS Browser Agent — an expert web automation specialist.

You control a real web browser to accomplish tasks. You can:
- Navigate to URLs
- Click buttons and links
- Fill in forms
- Extract text content
- Take screenshots
- Wait for elements
- Handle logins

When given a task, plan your browser actions step by step.
Report what you find and what actions you take.
"""


class BrowserAgent(BaseAgent):
    """Browser automation agent using Playwright.

    Wraps Playwright for web navigation, form filling, scraping.
    """

    name = "browser"

    def __init__(
        self,
        engine: InferenceEngine,
        model: str = "ollama/llama3.2",
        *,
        headless: bool = True,
    ) -> None:
        self._engine = engine
        self._model = model
        self._headless = headless
        self._playwright: Any = None
        self._browser: Any = None
        self._page: Any = None

    async def _ensure_browser(self) -> None:
        """Lazily initialize Playwright browser."""
        if self._browser is not None:
            return
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=self._headless)
            self._page = await self._browser.new_page()
            await self._page.set_extra_http_headers({"User-Agent": "AIOS Browser Agent 1.0"})
        except ImportError:
            self._browser = None  # Will use httpx fallback

    async def navigate(self, url: str) -> str:
        """Navigate to a URL and return page text content."""
        await self._ensure_browser()
        if self._page:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            text = await self._page.inner_text("body")
            return text[:5000]
        # Fallback: httpx
        import httpx

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "AIOS/1.0"})
            text = re.sub(r"<[^>]+>", " ", resp.text)
            return re.sub(r"\s+", " ", text).strip()[:5000]

    async def click(self, selector: str) -> str:
        """Click an element by CSS selector."""
        if self._page:
            try:
                await self._page.click(selector, timeout=5000)
                return f"Clicked: {selector}"
            except Exception as e:
                return f"Click failed: {e}"
        return "Browser not initialized"

    async def fill(self, selector: str, value: str) -> str:
        """Fill an input field."""
        if self._page:
            try:
                await self._page.fill(selector, value)
                return f"Filled '{selector}' with '{value[:50]}'"
            except Exception as e:
                return f"Fill failed: {e}"
        return "Browser not initialized"

    async def get_screenshot_b64(self) -> str:
        """Take a screenshot and return base64 encoded PNG."""
        if self._page:
            try:
                import base64

                screenshot = await self._page.screenshot()
                return base64.b64encode(screenshot).decode()
            except Exception as e:
                return f"Screenshot failed: {e}"
        return ""

    async def run(self, query: str, *, trace: Trace | None = None) -> str:
        """Execute a browser task guided by the LLM."""
        await self._ensure_browser()

        # Simple URL extraction — navigate if URL in query
        url_match = re.search(r"https?://[^\s]+", query)
        page_content = ""

        if url_match:
            url = url_match.group(0)
            page_content = await self.navigate(url)

        page_block = (
            f"Page content from {url_match.group(0)}:\n{page_content}"
            if url_match
            else "No URL provided in task."
        )

        context = f"""Task: {query}

{page_block}

Complete the browser task and report your findings."""

        messages = [
            Message(role=Role.SYSTEM, content=_BROWSER_SYSTEM),
            Message(role=Role.USER, content=context),
        ]
        result = await self._engine.complete(messages, model=self._model, max_tokens=2048)
        return result.content

    async def step(self, messages: list[Message], *, trace: Trace | None = None) -> Message:
        result = await self._engine.complete(messages, model=self._model)
        return Message(role=Role.ASSISTANT, content=result.content)

    async def close(self) -> None:
        """Clean up browser resources."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "BrowserAgent",
            "capabilities": ["navigate", "click", "fill_form", "screenshot", "scrape"],
            "model": self._model,
            "description": (
                "Automates web browsing with Playwright. Navigates, clicks, fills forms."
            ),
        }


__all__ = ["BrowserAgent"]
