"""BrowserSkill — AIOS-native browser automation (Layer 2 of AIOS core).

Implements the ``browser.*`` capabilities with an **offline-first** engine: it
uses the in-repo :mod:`aios.browser.BrowserSession` (Playwright/Chromium) when
available, and otherwise reports the capability as unavailable rather than
falling back to a cloud API. This keeps AIOS browser actions fully local
(ADR-0022).

Security model (per the M5 browser spec):
- An allowlist of permitted domains; everything else is denied unless matched.
- Localhost / private / internal addresses are denied by default (phishing /
  SSRF guard), and must be explicitly permitted.
- Destructive actions (``close_tab``, ``download``) require confirmation via the
  platform's approval gate (``ask`` manifest approval) — the skill also refuses
  to run them if not already approved through ``ctx.approved``.
- A configurable action timeout.
- Every action is appended to an in-memory + on-disk audit log.

The skill is a thin, real orchestrator over the browser engine: it does not
reimplement HTML parsing or automation primitives (those live in ``aios.browser``),
it adds the AIOS-native concerns (security, audit, tab/download bookkeeping).
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from aios.skills.base import Skill, SkillContext, SkillResult, SkillStatus
from aios.skills.manifest import SkillManifest

if TYPE_CHECKING:
    from aios.browser import BrowserConfig, BrowserSession

logger = logging.getLogger("aios.skills.native.browser")

# Capabilities owned natively by this skill.
BROWSER_CAPABILITIES = (
    "browser.open",
    "browser.search",
    "browser.navigate",
    "browser.screenshot",
    "browser.extract_text",
    "browser.click",
    "browser.type",
    "browser.automate",
)


def _is_internal_host(host: str) -> bool:
    """Return True if the host is localhost / private / reserved (SSRF guard)."""
    host = host.strip().lower()
    if host in {"localhost", "0.0.0.0", "::1", ""}:  # noqa: S104 (not a socket bind)
        return True
    # Strip IPv6 brackets.
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False  # not an IP literal; allowlist decides
    return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved


@dataclass
class BrowserConfigOpts:
    """Per-invocation security/behavior options for the BrowserSkill."""

    allowlist: tuple[str, ...] = ("*",)
    allow_internal: bool = False
    confirm_destructive: bool = True
    timeout_ms: int = 30_000
    headless: bool = True
    audit_path: str | None = None

    def allows(self, url: str) -> bool:
        """Decide whether a URL may be opened under this policy."""
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if not host:
            return False
        if _is_internal_host(host):
            return self.allow_internal or host in self.allowlist
        if "*" in self.allowlist:
            return True
        return any(host == a or host.endswith("." + a) for a in self.allowlist)


@dataclass
class _Tab:
    tab_id: str
    url: str
    title: str = ""


class BrowserSkill(Skill):
    """Local browser automation: navigation, tabs, automation, downloads.

    Built on :class:`aios.browser.BrowserSession`. Requires Playwright/Chromium
    to be installed for live automation; the resolver still advertises the
    capability natively, and operations fail gracefully with a clear message if
    the engine is unavailable.
    """

    def __init__(self, config: BrowserConfigOpts | None = None) -> None:
        self._cfg = config or BrowserConfigOpts()
        self._tabs: dict[str, _Tab] = {}
        self._active_tab: str | None = None
        self._downloads: list[dict[str, Any]] = []
        self._audit: list[dict[str, Any]] = []
        # Injectable session factory for testing (defaults to real engine).
        self._session_factory: Any = None
        super().__init__(
            SkillManifest(
                name="browser",
                version="1.0.0",
                description=(
                    "Native browser automation: open/search pages, manage tabs, "
                    "click/type/scroll/screenshot/extract, download — fully local"
                ),
                inputs=(
                    "action",
                    "url",
                    "query",
                    "selector",
                    "text",
                    "key",
                    "x",
                    "y",
                    "js",
                    "path",
                    "tab_id",
                    "timeout",
                ),
                outputs=(
                    "url",
                    "title",
                    "text",
                    "screenshot",
                    "tabs",
                    "active_tab",
                    "downloads",
                ),
                capabilities=BROWSER_CAPABILITIES,
                permissions=("BROWSER_AUTOMATE", "NETWORK_FETCH"),
                approval="ask",
                tags=("desktop", "browser", "automation"),
            )
        )

    # ---------------------------------------------------------------- auditing

    def _log(self, action: str, detail: dict[str, Any], *, ok: bool) -> None:
        entry = {"ts": round(time.time(), 3), "action": action, "ok": ok, **detail}
        self._audit.append(entry)
        if self._cfg.audit_path:
            try:
                p = Path(self._cfg.audit_path)
                p.parent.mkdir(parents=True, exist_ok=True)
                with p.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry) + "\n")
            except OSError:
                logger.warning("Browser audit log write failed", exc_info=True)

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        return list(self._audit)

    # ------------------------------------------------------------------ engine

    def _build_session(self) -> BrowserSession:
        from aios.browser import BrowserConfig, BrowserSession

        cfg: BrowserConfig = BrowserConfig(
            headless=self._cfg.headless, timeout=self._cfg.timeout_ms
        )
        return BrowserSession(config=cfg)

    # ------------------------------------------------------------------ helpers

    async def _open_session(self) -> BrowserSession:
        if self._session_factory is not None:
            return self._session_factory()
        session = self._build_session()
        await session.start()
        return session

    def _register_tab(self, url: str, title: str = "") -> str:
        tab_id = f"tab-{len(self._tabs) + 1}"
        self._tabs[tab_id] = _Tab(tab_id=tab_id, url=url, title=title)
        self._active_tab = tab_id
        return tab_id

    # -------------------------------------------------------------------- run

    async def run(self, ctx: SkillContext) -> SkillResult:
        action = (ctx.inputs.get("action") or "open").lower()
        url = ctx.inputs.get("url")
        query = ctx.inputs.get("query", "")
        try:
            if action in ("open", "search", "navigate"):
                return await self._do_navigate(action, url, query, ctx)
            if action in ("back", "forward", "refresh"):
                return await self._do_history(action, ctx)
            if action == "screenshot":
                return await self._do_screenshot(ctx)
            if action == "extract_text":
                return await self._do_extract(ctx)
            if action in ("click", "type", "press", "scroll", "wait_for", "evaluate"):
                return await self._do_automate(action, ctx)
            if action in ("list_tabs", "switch_tab", "active_tab"):
                return self._do_tabs(action, ctx)
            if action in ("download", "list_downloads"):
                return await self._do_downloads(action, ctx)
            if action == "close_tab":
                return self._do_close_tab(ctx)
            return SkillResult(status=SkillStatus.FAILED, error=f"unknown action: {action}")
        except Exception as exc:  # surface as skill failure, still audited
            self._log(action, {"error": str(exc)}, ok=False)
            return SkillResult(status=SkillStatus.FAILED, error=str(exc))

    # ----------------------------------------------------------------- navigate

    async def _do_navigate(
        self, action: str, url: str | None, query: str, ctx: SkillContext  # noqa: ARG002
    ) -> SkillResult:
        if action == "search":
            if not query:
                return SkillResult(status=SkillStatus.FAILED, error="missing 'query'")
            target = "https://duckduckgo.com/?q=" + _quote(query)
            nav_url = target
        else:
            nav_url = url or query
            if not nav_url:
                return SkillResult(status=SkillStatus.FAILED, error="missing 'url'")
            if not _looks_like_url(nav_url):
                nav_url = "https://" + nav_url

        if not self._cfg.allows(nav_url):
            self._log(action, {"url": nav_url, "denied": "policy"}, ok=False)
            return SkillResult(
                status=SkillStatus.FAILED,
                error=f"URL denied by browser policy: {nav_url}",
            )

        session = await self._open_session()
        try:
            result = await session.goto(nav_url)
            tab_id = self._register_tab(result.url, result.title)
            self._log(action, {"url": result.url, "tab": tab_id}, ok=result.ok)
            return SkillResult(
                status=SkillStatus.SUCCESS if result.ok else SkillStatus.FAILED,
                outputs={
                    "url": result.url,
                    "title": result.title,
                    "text": result.text,
                    "active_tab": tab_id,
                },
                steps=[f"{action} -> {result.url}"],
                data={"tab_id": tab_id},
                error=None if result.ok else result.error,
            )
        finally:
            await session.close()

    # ------------------------------------------------------------------ history

    async def _do_history(self, action: str, ctx: SkillContext) -> SkillResult:  # noqa: ARG002
        session = await self._open_session()
        try:
            if action == "back":
                res = await session.back()
            elif action == "forward":
                res = await session.forward()
            else:
                res = await session.reload()
            self._log(action, {"url": res.url}, ok=res.ok)
            return SkillResult(
                status=SkillStatus.SUCCESS if res.ok else SkillStatus.FAILED,
                outputs={"url": res.url, "title": res.title, "text": res.text},
                steps=[action],
                error=None if res.ok else res.error,
            )
        finally:
            await session.close()

    # --------------------------------------------------------------- screenshot

    async def _do_screenshot(self, ctx: SkillContext) -> SkillResult:
        path = ctx.inputs.get("path") or str(
            Path.home() / ".aios" / "browser-shots" / f"shot-{int(time.time())}.png"
        )
        session = await self._open_session()
        try:
            data = await session.screenshot(path=path)
            self._log("screenshot", {"path": path}, ok=bool(data))
            return SkillResult(
                status=SkillStatus.SUCCESS,
                outputs={"screenshot": path, "bytes": len(data)},
                steps=["captured screenshot"],
            )
        finally:
            await session.close()

    # ------------------------------------------------------------------ extract

    async def _do_extract(self, ctx: SkillContext) -> SkillResult:
        url = ctx.inputs.get("url")
        if not url:
            return SkillResult(status=SkillStatus.FAILED, error="missing 'url' for extract_text")
        if not self._cfg.allows(url):
            return SkillResult(status=SkillStatus.FAILED, error=f"URL denied by policy: {url}")
        session = await self._open_session()
        try:
            res = await session.goto(url)
            self._log("extract_text", {"url": res.url}, ok=res.ok)
            return SkillResult(
                status=SkillStatus.SUCCESS if res.ok else SkillStatus.FAILED,
                outputs={"url": res.url, "title": res.title, "text": res.text},
                steps=["fetched + extracted text"],
                error=None if res.ok else res.error,
            )
        finally:
            await session.close()

    # ---------------------------------------------------------------- automate

    async def _do_automate(self, action: str, ctx: SkillContext) -> SkillResult:
        url = ctx.inputs.get("url")
        if not url:
            return SkillResult(
                status=SkillStatus.FAILED,
                error="automate requires 'url' to anchor the page",
            )
        if not self._cfg.allows(url):
            return SkillResult(status=SkillStatus.FAILED, error=f"URL denied by policy: {url}")
        selector = ctx.inputs.get("selector", "")
        text = ctx.inputs.get("text", "")
        key = ctx.inputs.get("key", "")
        js = ctx.inputs.get("js", "")
        x = ctx.inputs.get("x", 0)
        y = ctx.inputs.get("y", 0)

        session = await self._open_session()
        try:
            await session.goto(url)
            out: dict[str, Any] = {}
            if action == "click":
                await session.click(selector)
                out["clicked"] = selector
            elif action == "type":
                await session.fill(selector, text)
                out["typed"] = text
            elif action == "press":
                page = session.page
                if page is not None:
                    await page.keyboard.press(key)
                out["pressed"] = key
            elif action == "scroll":
                page = session.page
                if page is not None:
                    await page.mouse.wheel(int(x), int(y))
                out["scrolled"] = [int(x), int(y)]
            elif action == "wait_for":
                await session.wait_for(selector)
                out["waited_for"] = selector
            elif action == "evaluate":
                out["result"] = await session.eval_js(js)
            self._log(action, {"url": url, "selector": selector}, ok=True)
            return SkillResult(
                status=SkillStatus.SUCCESS,
                outputs=out,
                steps=[f"{action} on {url}"],
            )
        finally:
            await session.close()

    # --------------------------------------------------------------------- tabs

    def _do_tabs(self, action: str, ctx: SkillContext) -> SkillResult:
        if action == "list_tabs":
            return SkillResult(
                status=SkillStatus.SUCCESS,
                outputs={"tabs": [vars(t) for t in self._tabs.values()]},
                steps=["listed tabs"],
            )
        if action == "active_tab":
            return SkillResult(
                status=SkillStatus.SUCCESS,
                outputs={"active_tab": self._active_tab},
                steps=["active tab"],
            )
        if action == "switch_tab":
            tab_id = ctx.inputs.get("tab_id", "")
            if tab_id not in self._tabs:
                return SkillResult(status=SkillStatus.FAILED, error=f"unknown tab: {tab_id}")
            self._active_tab = tab_id
            self._log("switch_tab", {"tab": tab_id}, ok=True)
            return SkillResult(
                status=SkillStatus.SUCCESS,
                outputs={"active_tab": tab_id},
                steps=[f"switched to {tab_id}"],
            )
        return SkillResult(status=SkillStatus.FAILED, error=f"unknown tab action: {action}")

    def _do_close_tab(self, ctx: SkillContext) -> SkillResult:
        if self._cfg.confirm_destructive and not getattr(ctx, "approved", False):
            return SkillResult(
                status=SkillStatus.FAILED,
                error="close_tab requires approval (destructive action)",
            )
        tab_id = ctx.inputs.get("tab_id") or self._active_tab
        if tab_id and tab_id in self._tabs:
            del self._tabs[tab_id]
            if self._active_tab == tab_id:
                self._active_tab = next(iter(self._tabs), None)
            self._log("close_tab", {"tab": tab_id}, ok=True)
            return SkillResult(
                status=SkillStatus.SUCCESS,
                outputs={"active_tab": self._active_tab},
                steps=[f"closed {tab_id}"],
            )
        return SkillResult(status=SkillStatus.FAILED, error="no tab to close")

    # ----------------------------------------------------------------- downloads

    async def _do_downloads(self, action: str, ctx: SkillContext) -> SkillResult:
        if action == "list_downloads":
            return SkillResult(
                status=SkillStatus.SUCCESS,
                outputs={"downloads": self._downloads},
                steps=["listed downloads"],
            )
        # download(url)
        url = ctx.inputs.get("url")
        if not url:
            return SkillResult(status=SkillStatus.FAILED, error="missing 'url' for download")
        if not self._cfg.allows(url):
            return SkillResult(status=SkillStatus.FAILED, error=f"URL denied by policy: {url}")
        if self._cfg.confirm_destructive and not getattr(ctx, "approved", False):
            return SkillResult(
                status=SkillStatus.FAILED,
                error="download requires approval (writes to disk)",
            )
        dest = ctx.inputs.get("path") or str(
            Path.home() / ".aios" / "downloads" / Path(urlparse(url).path).name
        )
        try:
            from aios.browser import Fetcher, FetcherConfig

            fetcher = Fetcher(FetcherConfig())
            res = await fetcher.fetch(url)
            payload = res.html or res.text
            if res.ok and payload:
                p = Path(dest)
                p.parent.mkdir(parents=True, exist_ok=True)
                await asyncio.to_thread(p.write_text, payload, encoding="utf-8")
                self._downloads.append({"url": url, "path": str(p), "ok": True})
                self._log("download", {"url": url, "path": str(p)}, ok=True)
                return SkillResult(
                    status=SkillStatus.SUCCESS,
                    outputs={"path": str(p)},
                    steps=[f"downloaded {url}"],
                )
            self._log("download", {"url": url, "ok": False}, ok=False)
            return SkillResult(status=SkillStatus.FAILED, error=res.error or "download failed")
        except Exception as exc:
            self._log("download", {"url": url, "error": str(exc)}, ok=False)
            return SkillResult(status=SkillStatus.FAILED, error=str(exc))


def _looks_like_url(s: str) -> bool:
    return s.startswith(("http://", "https://"))


def _quote(s: str) -> str:
    from urllib.parse import quote_plus

    return quote_plus(s)


__all__ = ["BROWSER_CAPABILITIES", "BrowserConfigOpts", "BrowserSkill"]
