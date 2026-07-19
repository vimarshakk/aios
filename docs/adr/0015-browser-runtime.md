# ADR-0015: Browser Runtime

**Date:** 2025-07-17
**Status:** Accepted
**Deciders:** Core team

## Context

M3.5 added browser runtime capabilities for web automation. This includes HTTP fetching, HTML parsing, and browser session management. The subsystem enables agents to interact with web services programmatically.

## Decision

Three-layer architecture:

- **Fetcher:** `httpx`-based HTTP client with retry, proxy support, SSL options. Returns `FetcherResult` with status, headers, body, timing.
- **Parser:** `selectolax`-based HTML parser (fast, lightweight). Extracts links, images, forms, meta tags. Returns `ParsedPage` with structured data.
- **BrowserSession:** `playwright`-based browser automation. Lazy import (playwright is optional). `launch()`, `goto()`, `click()`, `fill()`, `evaluate()`, `screenshot()`, `close()`. Returns `PageResult`.

## Consequences

- Playwright is a lazy import — if not installed, `BrowserSession` raises on `launch()`
- `selectolax` is preferred over BeautifulSoup for performance
- All components are async (httpx async, playwright async)
- `BrowserConfig` controls headless mode, viewport, proxy, timeouts
- `ParsedPage` includes `links`, `images`, `forms`, `meta` as structured dataclasses
- Screenshot returns raw bytes (PNG by default)

## Key Design Decisions

1. **Lazy playwright import:** Avoids hard dependency for users who only need fetch/parse
2. **selectolax over BeautifulSoup:** 10x faster for our use case
3. **httpx over requests:** Native async support, modern API
4. **Separate fetcher/parser/session:** Each layer is independently useful

## Alternatives Considered

1. **Selenium:** Slower, requires WebDriver, not async-native
2. **BeautifulSoup:** Slower parsing, heavier dependency
3. **aiohttp:** Good but httpx has better typing and sync/async parity

## References

- `packages/browser/src/aios/browser/fetcher.py`
- `packages/browser/src/aios/browser/parser.py`
- `packages/browser/src/aios/browser/browser.py`
- `tests/test_browser.py`
