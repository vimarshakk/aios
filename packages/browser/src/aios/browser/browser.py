"""Playwright-based browser automation — full browser control for JS-heavy pages.

Provides BrowserSession as an async context manager wrapping Playwright's
Chromium, with methods for navigation, interaction, screenshots, and JS execution.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from selectolax.parser import HTMLParser

if TYPE_CHECKING:
    from pathlib import Path

    from playwright.async_api import Browser, BrowserContext, Page, Playwright


@dataclass
class BrowserConfig:
    """Configuration for browser automation.

    Attributes:
        headless: Run browser in headless mode (default True).
        viewport_width: Browser viewport width in pixels.
        viewport_height: Browser viewport height in pixels.
        user_agent: Custom user agent string.
        timeout: Default navigation/action timeout in ms.
        slow_mo: Slow down Playwright operations by this many ms (debugging).
        args: Additional Chromium launch arguments.
    """

    headless: bool = True
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: str = ""
    timeout: float = 30_000
    slow_mo: float = 0
    args: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PageResult:
    """Result of a page navigation or interaction.

    Attributes:
        url: Final URL after navigation.
        title: Page title.
        content: Raw HTML content.
        text: Extracted plain text.
        status: HTTP response status code.
        elapsed_ms: Total operation time in milliseconds.
        ok: True if no error occurred.
        error: Error message if the operation failed.
    """

    url: str
    title: str
    content: str
    text: str
    status: int
    elapsed_ms: float
    ok: bool
    error: str | None = None


class BrowserSession:
    """Async context manager for Playwright browser automation.

    Usage::

        async with BrowserSession() as session:
            result = await session.goto("https://example.com")
            print(result.text)
            await session.screenshot(Path("shot.png"))
    """

    def __init__(self, config: BrowserConfig | None = None) -> None:
        self._config = config or BrowserConfig()
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page | None:
        return self._page

    @property
    def is_open(self) -> bool:
        return self._page is not None

    async def __aenter__(self) -> BrowserSession:
        await self.start()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def start(self) -> None:
        """Launch the browser and create a page."""
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise ImportError(
                "Playwright is required for BrowserSession. "
                "Install with: pip install playwright && playwright install chromium"
            ) from exc
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._config.headless,
            slow_mo=self._config.slow_mo or None,
            args=self._config.args or None,
        )
        context_opts: dict[str, Any] = {
            "viewport": {
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            },
        }
        if self._config.user_agent:
            context_opts["user_agent"] = self._config.user_agent
        self._context = await self._browser.new_context(**context_opts)
        self._context.set_default_timeout(self._config.timeout)
        self._page = await self._context.new_page()

    async def close(self) -> None:
        """Close the browser and clean up resources."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._page = None

    async def goto(
        self,
        url: str,
        wait_until: str = "load",
        timeout: float | None = None,
    ) -> PageResult:
        """Navigate to a URL.

        Args:
            url: Target URL.
            wait_until: Wait strategy — "load", "domcontentloaded", or "networkidle".
            timeout: Navigation timeout override in ms.

        Returns:
            PageResult with page content.
        """
        self._assert_page()
        start = time.monotonic()
        try:
            resp = await self._page.goto(url, wait_until=wait_until, timeout=timeout)
            status = resp.status if resp else 0
            elapsed_ms = (time.monotonic() - start) * 1000
            return await self._build_result(status=status, elapsed_ms=elapsed_ms)
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            return PageResult(
                url=url,
                title="",
                content="",
                text="",
                status=0,
                elapsed_ms=round(elapsed_ms, 2),
                ok=False,
                error=str(exc),
            )

    async def click(self, selector: str, timeout: float | None = None) -> None:
        """Click an element by CSS selector."""
        self._assert_page()
        await self._page.click(selector, timeout=timeout)

    async def fill(self, selector: str, value: str, timeout: float | None = None) -> None:
        """Fill an input field with a value."""
        self._assert_page()
        await self._page.fill(selector, value, timeout=timeout)

    async def select_option(
        self,
        selector: str,
        value: str,
        timeout: float | None = None,
    ) -> None:
        """Select an option from a <select> element."""
        self._assert_page()
        await self._page.select_option(selector, value=value, timeout=timeout)

    async def eval_js(self, expression: str) -> Any:
        """Execute JavaScript in the page context.

        Args:
            expression: JavaScript expression to evaluate.

        Returns:
            The result of the expression.
        """
        self._assert_page()
        return await self._page.evaluate(expression)

    async def screenshot(
        self,
        path: str | Path | None = None,
        *,
        full_page: bool = True,
    ) -> bytes:
        """Capture a screenshot.

        Args:
            path: Optional file path to save the screenshot.
            full_page: Capture the full scrollable page.

        Returns:
            Raw PNG bytes of the screenshot.
        """
        self._assert_page()
        return await self._page.screenshot(path=str(path) if path else None, full_page=full_page)

    async def pdf(
        self,
        path: str | Path | None = None,
    ) -> bytes:
        """Generate a PDF of the page.

        Note: Only works in headless Chromium.

        Args:
            path: Optional file path to save the PDF.

        Returns:
            Raw PDF bytes.
        """
        self._assert_page()
        return await self._page.pdf(path=str(path) if path else None)

    async def wait_for(
        self,
        selector: str,
        state: str = "visible",
        timeout: float | None = None,
    ) -> None:
        """Wait for an element to reach a specific state.

        Args:
            selector: CSS selector to wait for.
            state: One of "attached", "detached", "visible", "hidden".
            timeout: Timeout override in ms.
        """
        self._assert_page()
        await self._page.wait_for_selector(selector, state=state, timeout=timeout)

    async def back(self) -> PageResult:
        """Navigate back in history."""
        self._assert_page()
        start = time.monotonic()
        await self._page.go_back()
        elapsed_ms = (time.monotonic() - start) * 1000
        return await self._build_result(elapsed_ms=elapsed_ms)

    async def forward(self) -> PageResult:
        """Navigate forward in history."""
        self._assert_page()
        start = time.monotonic()
        await self._page.go_forward()
        elapsed_ms = (time.monotonic() - start) * 1000
        return await self._build_result(elapsed_ms=elapsed_ms)

    async def reload(self, wait_until: str = "load") -> PageResult:
        """Reload the current page."""
        self._assert_page()
        start = time.monotonic()
        await self._page.reload(wait_until=wait_until)
        elapsed_ms = (time.monotonic() - start) * 1000
        return await self._build_result(elapsed_ms=elapsed_ms)

    async def get_content(self) -> str:
        """Get the raw HTML content of the current page."""
        self._assert_page()
        return await self._page.content()

    async def get_title(self) -> str:
        """Get the title of the current page."""
        self._assert_page()
        return await self._page.title()

    async def get_url(self) -> str:
        """Get the URL of the current page."""
        self._assert_page()
        return self._page.url

    def _assert_page(self) -> None:
        if self._page is None:
            raise RuntimeError("BrowserSession is not open. Call start() first.")

    async def _build_result(
        self,
        status: int = 200,
        elapsed_ms: float = 0,
    ) -> PageResult:
        content = await self._page.content()
        title = await self._page.title()
        url = self._page.url
        tree = HTMLParser(content)
        text = tree.body.text(strip=True) if tree.body else tree.html()
        return PageResult(
            url=url,
            title=title,
            content=content,
            text=text,
            status=status,
            elapsed_ms=round(elapsed_ms, 2),
            ok=True,
        )


__all__ = [
    "BrowserConfig",
    "BrowserSession",
    "PageResult",
]
