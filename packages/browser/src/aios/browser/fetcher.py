"""Lightweight HTTP fetcher — fast, async, httpx-based.

Provides a simple interface for fetching web content without launching
a full browser. Supports redirects, custom headers, timeouts, and
automatic HTML-to-text extraction via selectolax.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from selectolax.parser import HTMLParser


@dataclass(frozen=True)
class FetchResult:
    """Result of an HTTP fetch operation.

    Attributes:
        url: Final URL after redirects.
        status: HTTP status code.
        headers: Response headers.
        text: Extracted plain text content (stripped of HTML).
        html: Raw HTML content.
        elapsed_ms: Total request time in milliseconds.
        ok: True if status is 2xx.
        error: Error message if the request failed, None otherwise.
    """

    url: str
    status: int
    headers: dict[str, str]
    text: str
    html: str
    elapsed_ms: float
    ok: bool
    error: str | None = None


@dataclass
class FetcherConfig:
    """Configuration for the Fetcher.

    Attributes:
        timeout: Default request timeout in seconds.
        max_redirects: Maximum number of redirects to follow.
        user_agent: Default User-Agent header.
        default_headers: Headers sent with every request.
    """

    timeout: float = 30.0
    max_redirects: int = 10
    user_agent: str = "AIOsBrowser/1.0 (+https://aios.dev)"
    default_headers: dict[str, str] = field(default_factory=dict)


class Fetcher:
    """Async HTTP fetcher backed by httpx.

    Lightweight alternative to full browser automation for pages
    that don't require JavaScript execution.

    Usage::

        fetcher = Fetcher(config=FetcherConfig(timeout=15))
        result = await fetcher.get("https://example.com")
        print(result.text)
    """

    def __init__(self, config: FetcherConfig | None = None) -> None:
        self._config = config or FetcherConfig()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._config.timeout,
                max_redirects=self._config.max_redirects,
                headers={"User-Agent": self._config.user_agent, **self._config.default_headers},
                follow_redirects=True,
            )
        return self._client

    async def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> FetchResult:
        return await self._fetch("GET", url, headers=headers, params=params)

    async def post(
        self,
        url: str,
        data: Any | None = None,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> FetchResult:
        return await self._fetch("POST", url, headers=headers, data=data, json_body=json)

    async def put(
        self,
        url: str,
        data: Any | None = None,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> FetchResult:
        return await self._fetch("PUT", url, headers=headers, data=data, json_body=json)

    async def delete(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> FetchResult:
        return await self._fetch("DELETE", url, headers=headers)

    async def patch(
        self,
        url: str,
        data: Any | None = None,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> FetchResult:
        return await self._fetch("PATCH", url, headers=headers, data=data, json_body=json)

    async def _fetch(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        json_body: Any | None = None,
    ) -> FetchResult:
        client = await self._get_client()
        start = time.monotonic()
        try:
            resp = await client.request(
                method,
                url,
                headers=headers,
                params=params,
                data=data,
                json=json_body,
            )
            elapsed_ms = (time.monotonic() - start) * 1000
            html = resp.text
            tree = HTMLParser(html)
            text = tree.body.text(strip=True) if tree.body else tree.html()
            return FetchResult(
                url=str(resp.url),
                status=resp.status_code,
                headers=dict(resp.headers),
                text=text,
                html=html,
                elapsed_ms=round(elapsed_ms, 2),
                ok=200 <= resp.status_code < 300,
            )
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            return FetchResult(
                url=url,
                status=0,
                headers={},
                text="",
                html="",
                elapsed_ms=round(elapsed_ms, 2),
                ok=False,
                error=str(exc),
            )

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> Fetcher:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()


__all__ = [
    "FetchResult",
    "Fetcher",
    "FetcherConfig",
]
