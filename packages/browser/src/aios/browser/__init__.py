"""AIOS Browser Runtime.

Lightweight HTTP fetcher and Playwright-based browser automation
for web interaction, content extraction, and screenshot capture.
"""

from __future__ import annotations

from aios.browser.browser import BrowserConfig, BrowserSession, PageResult
from aios.browser.fetcher import Fetcher, FetcherConfig, FetchResult
from aios.browser.parser import ParsedPage, parse_html

API_VERSION = "1.0"

__all__ = [
    "API_VERSION",
    "BrowserConfig",
    "BrowserSession",
    "FetchResult",
    "Fetcher",
    "FetcherConfig",
    "PageResult",
    "ParsedPage",
    "parse_html",
]
