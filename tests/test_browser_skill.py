"""Tests for the native BrowserSkill (offline policy, automation, registration).

Real browser automation needs Playwright/Chromium; these tests inject a fake
session to exercise the skill's policy, security, tab bookkeeping, audit log, and
Supervisor/planner integration without launching a browser.
"""

from __future__ import annotations

from dataclasses import dataclass

from aios.platform import CapabilityResolver, DeveloperPlatform, ProviderKind
from aios.skills.base import SkillContext, SkillStatus
from aios.skills.native import BrowserConfigOpts, BrowserSkill, register_native_skills
from aios.skills.registry import SkillRegistry


@dataclass
class _FakeResult:
    url: str
    title: str = "Title"
    text: str = "body text"
    content: str = "<html></html>"
    status: int = 200
    elapsed_ms: float = 1.0
    ok: bool = True
    error: str | None = None


class _FakeSession:
    """Minimal async session faking aios.browser.BrowserSession behavior."""

    def __init__(self) -> None:
        self.page = _FakePage()
        self.last: dict = {}

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def goto(self, url: str, **kw: object) -> _FakeResult:
        self.last["goto"] = url
        return _FakeResult(url=url)

    async def click(self, selector: str, **kw: object) -> None:
        self.last["click"] = selector

    async def fill(self, selector: str, value: str, **kw: object) -> None:
        self.last["fill"] = (selector, value)

    async def wait_for(self, selector: str, **kw: object) -> None:
        self.last["wait_for"] = selector

    async def eval_js(self, expression: str) -> object:
        self.last["eval_js"] = expression
        return {"result": 42}

    async def screenshot(self, path: str | None = None, **kw: object) -> bytes:
        self.last["screenshot"] = path
        return b"png"

    async def back(self) -> _FakeResult:
        return _FakeResult(url="https://back.example")

    async def forward(self) -> _FakeResult:
        return _FakeResult(url="https://fwd.example")

    async def reload(self) -> _FakeResult:
        return _FakeResult(url="https://reload.example")


class _FakePage:
    def __init__(self) -> None:
        self.keyboard = _FakeKeyboard()
        self.mouse = _FakeMouse()


class _FakeKeyboard:
    def __init__(self) -> None:
        self.pressed: list[str] = []

    async def press(self, key: str) -> None:
        self.pressed.append(key)


class _FakeMouse:
    def __init__(self) -> None:
        self.wheeled: list[tuple[int, int]] = []

    async def wheel(self, x: int, y: int) -> None:
        self.wheeled.append((x, y))


def _skill() -> BrowserSkill:
    skill = BrowserSkill(BrowserConfigOpts(allowlist=("*",)))
    fake = _FakeSession()
    skill._session_factory = lambda: fake  # type: ignore[assignment]
    skill._fake = fake  # type: ignore[attr-defined]
    return skill


async def test_open_navigates_and_registers_tab() -> None:
    skill = _skill()
    res = await skill.run(SkillContext(skill_name="browser", inputs={"action": "open", "url": "https://example.com"}))
    assert res.status == SkillStatus.SUCCESS
    assert res.outputs["url"] == "https://example.com"
    assert skill._fake.last["goto"] == "https://example.com"
    assert skill._active_tab is not None
    assert skill.audit_log
    assert skill.audit_log[-1]["action"] == "open"


async def test_search_builds_query_url() -> None:
    skill = _skill()
    res = await skill.run(
        SkillContext(skill_name="browser", inputs={"action": "search", "query": "AIOS agent"})
    )
    assert res.status == SkillStatus.SUCCESS
    assert "duckduckgo.com" in skill._fake.last["goto"]
    assert "AIOS" in skill._fake.last["goto"]


async def test_internal_url_denied_by_policy() -> None:
    skill = BrowserSkill(BrowserConfigOpts(allowlist=("*",), allow_internal=False))
    fake = _FakeSession()
    skill._session_factory = lambda: fake  # type: ignore[assignment]
    res = await skill.run(
        SkillContext(skill_name="browser", inputs={"action": "open", "url": "http://localhost:8080"})
    )
    assert res.status == SkillStatus.FAILED
    assert "policy" in res.error


async def test_internal_url_allowed_when_permitted() -> None:
    skill = BrowserSkill(BrowserConfigOpts(allowlist=("*",), allow_internal=True))
    fake = _FakeSession()
    skill._session_factory = lambda: fake  # type: ignore[assignment]
    res = await skill.run(
        SkillContext(skill_name="browser", inputs={"action": "open", "url": "http://localhost:8080"})
    )
    assert res.status == SkillStatus.SUCCESS


async def test_click_and_type_automation() -> None:
    skill = _skill()
    res = await skill.run(
        SkillContext(
            skill_name="browser",
            inputs={"action": "click", "url": "https://example.com", "selector": "#btn"},
        )
    )
    assert res.status == SkillStatus.SUCCESS
    assert skill._fake.last["click"] == "#btn"

    res2 = await skill.run(
        SkillContext(
            skill_name="browser",
            inputs={"action": "type", "url": "https://example.com", "selector": "#q", "text": "hi"},
        )
    )
    assert res2.status == SkillStatus.SUCCESS
    assert skill._fake.last["fill"] == ("#q", "hi")


async def test_screenshot_writes_path(tmp_path) -> None:
    skill = _skill()
    shot = tmp_path / "shot.png"
    res = await skill.run(
        SkillContext(skill_name="browser", inputs={"action": "screenshot", "path": str(shot)})
    )
    assert res.status == SkillStatus.SUCCESS
    assert res.outputs["screenshot"] == str(shot)
    assert skill._fake.last["screenshot"] == str(shot)


async def test_extract_text() -> None:
    skill = _skill()
    res = await skill.run(
        SkillContext(skill_name="browser", inputs={"action": "extract_text", "url": "https://example.com"})
    )
    assert res.status == SkillStatus.SUCCESS
    assert "body text" in res.outputs["text"]


async def test_close_tab_requires_approval() -> None:
    skill = _skill()
    await skill.run(SkillContext(skill_name="browser", inputs={"action": "open", "url": "https://example.com"}))
    # Without approval, destructive action is refused.
    res = await skill.run(SkillContext(skill_name="browser", inputs={"action": "close_tab"}))
    assert res.status == SkillStatus.FAILED
    assert "approval" in res.error
    # With approval flag set, it succeeds.
    ctx = SkillContext(skill_name="browser", inputs={"action": "close_tab"})
    ctx.approved = True  # type: ignore[attr-defined]
    res2 = await skill.run(ctx)
    assert res2.status == SkillStatus.SUCCESS


async def test_tab_management() -> None:
    skill = _skill()
    await skill.run(SkillContext(skill_name="browser", inputs={"action": "open", "url": "https://a.example"}))
    await skill.run(SkillContext(skill_name="browser", inputs={"action": "open", "url": "https://b.example"}))
    listed = await skill.run(SkillContext(skill_name="browser", inputs={"action": "list_tabs"}))
    assert len(listed.outputs["tabs"]) == 2
    active = await skill.run(SkillContext(skill_name="browser", inputs={"action": "active_tab"}))
    assert active.outputs["active_tab"]


async def test_register_with_resolver() -> None:
    reg = SkillRegistry()
    resolver = CapabilityResolver(skills=reg)
    register_native_skills(reg, resolver)
    # browser.* capabilities resolve natively to the browser skill.
    r = resolver.resolve("browser.open")
    assert r.provider_kind == ProviderKind.NATIVE
    assert r.provider_id == "browser"
    # Platform bootstrap wires it too.
    platform = DeveloperPlatform()
    platform.bootstrap()
    pr = platform.resolve("browser.screenshot")
    assert pr.provider_kind == ProviderKind.NATIVE
    assert pr.provider_id == "browser"


def test_browser_in_native_skill_names() -> None:
    reg = SkillRegistry()
    resolver = CapabilityResolver(skills=reg)
    register_native_skills(reg, resolver)
    assert "browser" in reg.names
