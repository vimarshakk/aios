"""Tests for M3.5 — Browser Runtime.

Covers: fetcher, parser, browser session.
Browser tests require Playwright chromium to be installed (skipped otherwise).
"""

from __future__ import annotations

import socket

import pytest

from aios.browser.browser import BrowserConfig, BrowserSession, PageResult
from aios.browser.fetcher import Fetcher, FetcherConfig, FetchResult
from aios.browser.parser import FormData, FormField, Image, Link, parse_html

# Live-network tests (httpbin.org / localhost). Skip when offline so the
# suite stays runnable in sandboxed/CI environments without egress.
def _network_available() -> bool:
    try:
        with socket.create_connection(("httpbin.org", 443), timeout=3):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.network

# ── Parser (pure, no network) ──────────────────────────────────────────

SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="description" content="Test page">
    <meta property="og:title" content="OG Title">
    <title>Hello World</title>
</head>
<body>
    <h1>Welcome</h1>
    <p>This is a test page.</p>
    <a href="/about" rel="nofollow">About Us</a>
    <a href="https://example.com">External</a>
    <img src="/logo.png" alt="Logo" width="100" height="50">
    <img src="/banner.jpg" alt="">
    <form action="/submit" method="post">
        <input name="email" type="email" placeholder="you@example.com" required>
        <input name="password" type="password" value="">
        <select name="country">
            <option value="us">US</option>
        </select>
        <textarea name="bio"></textarea>
        <button type="submit">Go</button>
    </form>
    <form action="/search" method="get">
        <input name="q" type="search" placeholder="Search">
    </form>
</body>
</html>"""


class TestParseHtml:
    def test_title(self):
        p = parse_html(SAMPLE_HTML)
        assert p.title == "Hello World"

    def test_text(self):
        p = parse_html(SAMPLE_HTML)
        assert "Welcome" in p.text
        assert "test page" in p.text

    def test_links_count(self):
        p = parse_html(SAMPLE_HTML)
        assert len(p.links) == 2

    def test_link_href(self):
        p = parse_html(SAMPLE_HTML)
        about = next(link for link in p.links if link.text == "About Us")
        assert about.href == "/about"
        assert about.rel == "nofollow"

    def test_link_external(self):
        p = parse_html(SAMPLE_HTML)
        ext = next(link for link in p.links if link.href == "https://example.com")
        assert ext.text == "External"

    def test_images_count(self):
        p = parse_html(SAMPLE_HTML)
        assert len(p.images) == 2

    def test_image_attrs(self):
        p = parse_html(SAMPLE_HTML)
        logo = next(i for i in p.images if i.src == "/logo.png")
        assert logo.alt == "Logo"
        assert logo.width == "100"
        assert logo.height == "50"

    def test_image_no_alt(self):
        p = parse_html(SAMPLE_HTML)
        banner = next(i for i in p.images if i.src == "/banner.jpg")
        assert banner.alt is None

    def test_forms_count(self):
        p = parse_html(SAMPLE_HTML)
        assert len(p.forms) == 2

    def test_form_post_action(self):
        p = parse_html(SAMPLE_HTML)
        submit = next(f for f in p.forms if f.action == "/submit")
        assert submit.method == "POST"
        assert len(submit.fields) == 4

    def test_form_get_action(self):
        p = parse_html(SAMPLE_HTML)
        search = next(f for f in p.forms if f.action == "/search")
        assert search.method == "GET"
        assert len(search.fields) == 1

    def test_form_field_name(self):
        p = parse_html(SAMPLE_HTML)
        submit = next(f for f in p.forms if f.action == "/submit")
        email = next(f for f in submit.fields if f.name == "email")
        assert email.field_type == "email"
        assert email.placeholder == "you@example.com"
        assert email.required is True

    def test_form_field_password(self):
        p = parse_html(SAMPLE_HTML)
        submit = next(f for f in p.forms if f.action == "/submit")
        pw = next(f for f in submit.fields if f.name == "password")
        assert pw.field_type == "password"

    def test_meta_count(self):
        p = parse_html(SAMPLE_HTML)
        assert len(p.meta) == 2

    def test_meta_description(self):
        p = parse_html(SAMPLE_HTML)
        desc = next(m for m in p.meta if m.name == "description")
        assert desc.content == "Test page"

    def test_meta_og_title(self):
        p = parse_html(SAMPLE_HTML)
        og = next(m for m in p.meta if m.name == "og:title")
        assert og.content == "OG Title"

    def test_charset(self):
        p = parse_html(SAMPLE_HTML)
        assert p.charset == "utf-8"

    def test_language(self):
        p = parse_html(SAMPLE_HTML)
        assert p.language == "en"

    def test_empty_html(self):
        p = parse_html("")
        assert p.title == ""
        assert p.text == ""
        assert p.links == ()
        assert p.images == ()

    def test_no_body(self):
        p = parse_html("<html><head><title>T</title></head></html>")
        assert p.title == "T"

    def test_links_are_frozen(self):
        p = parse_html(SAMPLE_HTML)
        assert isinstance(p.links[0], Link)
        assert isinstance(p.images[0], Image)
        assert isinstance(p.forms[0], FormData)
        assert isinstance(p.forms[0].fields[0], FormField)

    def test_plain_text_only(self):
        p = parse_html("<p>Just text, no tags</p>")
        assert p.text == "Just text, no tags"
        assert p.links == ()
        assert p.images == ()


# ── Fetcher Config ─────────────────────────────────────────────────────


class TestFetcherConfig:
    def test_defaults(self):
        c = FetcherConfig()
        assert c.timeout == 30.0
        assert c.max_redirects == 10
        assert "AIOsBrowser" in c.user_agent

    def test_custom(self):
        c = FetcherConfig(timeout=5.0, max_redirects=2, user_agent="Custom/1.0")
        assert c.timeout == 5.0
        assert c.max_redirects == 2
        assert c.user_agent == "Custom/1.0"


# ── FetchResult ────────────────────────────────────────────────────────


class TestFetchResult:
    def test_ok_on_200(self):
        r = FetchResult(
            url="https://example.com", status=200, headers={},
            text="", html="", elapsed_ms=10, ok=True,
        )
        assert r.ok is True

    def test_not_ok_on_404(self):
        r = FetchResult(
            url="https://example.com/missing", status=404, headers={},
            text="", html="", elapsed_ms=10, ok=False,
        )
        assert r.ok is False

    def test_error_field(self):
        r = FetchResult(
            url="https://example.com", status=0, headers={},
            text="", html="", elapsed_ms=10, ok=False, error="timeout",
        )
        assert r.error == "timeout"


# ── Fetcher (async) ────────────────────────────────────────────────────


class TestFetcher:
    @pytest.mark.anyio
    async def test_context_manager(self):
        async with Fetcher() as f:
            result = await f.get("https://httpbin.org/get")
            assert result.ok is True
            assert f._client is not None

    @pytest.mark.anyio
    async def test_fetch_real_page(self):
        async with Fetcher(config=FetcherConfig(timeout=10)) as f:
            result = await f.get("https://httpbin.org/get")
            assert result.ok is True
            assert result.status == 200
            assert result.elapsed_ms > 0

    @pytest.mark.anyio
    async def test_fetch_404(self):
        async with Fetcher(config=FetcherConfig(timeout=10)) as f:
            result = await f.get("https://httpbin.org/status/404")
            assert result.ok is False
            assert result.status == 404

    @pytest.mark.anyio
    async def test_fetch_bad_url(self):
        async with Fetcher(config=FetcherConfig(timeout=5)) as f:
            result = await f.get("http://localhost:19999/nope")
            assert result.ok is False
            assert result.error is not None

    @pytest.mark.anyio
    async def test_get_html_populated(self):
        async with Fetcher(config=FetcherConfig(timeout=10)) as f:
            result = await f.get("https://httpbin.org/html")
            assert result.ok is True
            assert "<html" in result.html.lower()
            assert len(result.text) > 0

    @pytest.mark.anyio
    async def test_post_method(self):
        async with Fetcher(config=FetcherConfig(timeout=10)) as f:
            result = await f.post("https://httpbin.org/post", json={"key": "val"})
            assert result.ok is True

    @pytest.mark.anyio
    async def test_headers_passed(self):
        async with Fetcher() as f:
            result = await f.get(
                "https://httpbin.org/headers",
                headers={"X-Custom": "test123"},
            )
            assert result.ok is True
            assert "test123" in result.text


# ── BrowserConfig ──────────────────────────────────────────────────────


class TestBrowserConfig:
    def test_defaults(self):
        c = BrowserConfig()
        assert c.headless is True
        assert c.viewport_width == 1280
        assert c.viewport_height == 720
        assert c.timeout == 30_000

    def test_custom(self):
        c = BrowserConfig(headless=False, viewport_width=800, viewport_height=600)
        assert c.headless is False
        assert c.viewport_width == 800


# ── PageResult ─────────────────────────────────────────────────────────


class TestPageResult:
    def test_ok_result(self):
        r = PageResult(
            url="https://example.com", title="Ex", content="<html>",
            text="Ex", status=200, elapsed_ms=100, ok=True,
        )
        assert r.ok is True
        assert r.title == "Ex"

    def test_error_result(self):
        r = PageResult(
            url="https://example.com", title="", content="",
            text="", status=0, elapsed_ms=50, ok=False, error="timeout",
        )
        assert r.ok is False
        assert r.error == "timeout"


# ── BrowserSession (requires Playwright) ───────────────────────────────

try:
    import importlib.util as _ilu
    _has_pw = _ilu.find_spec("playwright") is not None
except Exception:
    _has_pw = False

pytestmark_browser = pytest.mark.skipif(not _has_pw, reason="Playwright not installed")


@pytestmark_browser
class TestBrowserSession:
    @pytest.mark.anyio
    async def test_context_manager(self):
        async with BrowserSession() as s:
            assert s.is_open

    @pytest.mark.anyio
    async def test_goto_example(self):
        async with BrowserSession() as s:
            r = await s.goto("https://example.com")
            assert r.ok is True
            assert "Example" in r.title

    @pytest.mark.anyio
    async def test_get_title(self):
        async with BrowserSession() as s:
            await s.goto("https://example.com")
            title = await s.get_title()
            assert "Example" in title

    @pytest.mark.anyio
    async def test_get_url(self):
        async with BrowserSession() as s:
            await s.goto("https://example.com")
            url = await s.get_url()
            assert "example.com" in url

    @pytest.mark.anyio
    async def test_get_content(self):
        async with BrowserSession() as s:
            await s.goto("https://example.com")
            html = await s.get_content()
            assert "<html" in html.lower()

    @pytest.mark.anyio
    async def test_screenshot_returns_bytes(self):
        async with BrowserSession() as s:
            await s.goto("https://example.com")
            data = await s.screenshot()
            assert isinstance(data, bytes)
            assert len(data) > 0

    @pytest.mark.anyio
    async def test_eval_js(self):
        async with BrowserSession() as s:
            await s.goto("https://example.com")
            title = await s.eval_js("document.title")
            assert "Example" in title

    @pytest.mark.anyio
    async def test_click(self):
        async with BrowserSession() as s:
            await s.goto("https://example.com")
            await s.click("a")

    @pytest.mark.anyio
    async def test_reload(self):
        async with BrowserSession() as s:
            await s.goto("https://example.com")
            r = await s.reload()
            assert r.ok is True

    @pytest.mark.anyio
    async def test_back_forward(self):
        async with BrowserSession() as s:
            await s.goto("https://example.com")
            await s.goto("https://httpbin.org/get")
            r = await s.back()
            assert r.ok is True

    @pytest.mark.anyio
    async def test_page_property(self):
        async with BrowserSession() as s:
            assert s.page is not None

    @pytest.mark.anyio
    async def test_not_open_before_start(self):
        s = BrowserSession()
        assert s.is_open is False
        assert s.page is None

    @pytest.mark.anyio
    async def test_assert_page_raises(self):
        s = BrowserSession()
        with pytest.raises(RuntimeError, match="not open"):
            await s.goto("https://example.com")

    @pytest.mark.anyio
    async def test_wait_for_selector(self):
        async with BrowserSession() as s:
            await s.goto("https://example.com")
            await s.wait_for("h1", state="visible")

    @pytest.mark.anyio
    async def test_fill_and_click(self):
        async with BrowserSession() as s:
            await s.goto("https://httpbin.org/forms/post")
            await s.fill("input[name='custname']", "Test User")
            await s.fill("textarea[name='comments']", "Hello from tests")

    @pytest.mark.anyio
    async def test_pdf(self):
        async with BrowserSession() as s:
            await s.goto("https://example.com")
            data = await s.pdf()
            assert isinstance(data, bytes)
            assert len(data) > 0

    @pytest.mark.anyio
    async def test_screenshot_saves_to_file(self, tmp_path):
        path = tmp_path / "shot.png"
        async with BrowserSession() as s:
            await s.goto("https://example.com")
            await s.screenshot(path=path)
            assert path.exists()
            assert path.stat().st_size > 0
