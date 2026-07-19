"""Tests for the CapabilityResolver (native-first provider selection)."""

from __future__ import annotations

from aios.platform import (
    CapabilityResolver,
    DeveloperPlatform,
    ProviderKind,
    Resolution,
)
from aios.skills.registry import SkillRegistry


def test_native_preferred_over_optional() -> None:
    reg = SkillRegistry()
    res = CapabilityResolver(skills=reg)
    reg.register(_DummySkill("notes-markdown"))
    res.register_native_skill("notes.write", "notes-markdown")
    # Optional provider available, but native must win.
    res.register_provider(
        "notes.write", "composio.notion", ProviderKind.CONNECTOR, lambda: True
    )
    r = res.resolve("notes.write")
    assert r.provider_kind == ProviderKind.NATIVE
    assert r.provider_id == "notes-markdown"
    assert r.available is True


def test_optional_used_when_no_native() -> None:
    res = CapabilityResolver(skills=SkillRegistry())
    res.register_provider(
        "email.send", "composio.gmail", ProviderKind.CONNECTOR, lambda: True
    )
    r = res.resolve("email.send")
    assert r.provider_kind == ProviderKind.CONNECTOR
    assert r.available is True


def test_unavailable_provider_reported() -> None:
    res = CapabilityResolver(skills=SkillRegistry())
    res.register_provider(
        "email.send", "composio.gmail", ProviderKind.CONNECTOR, lambda: False
    )
    r = res.resolve("email.send")
    assert r.provider_id == "composio.gmail"
    assert r.available is False
    assert "not currently available" in r.reason


def test_unknown_capability() -> None:
    res = CapabilityResolver(skills=SkillRegistry())
    r = res.resolve("does.not.exist")
    assert r.resolved is False
    assert r.provider_id is None


def test_platform_resolve_integration() -> None:
    platform = DeveloperPlatform()
    platform.bootstrap()
    # terminal is a native skill registered at bootstrap.
    r: Resolution = platform.resolve("terminal.exec")
    assert r.provider_kind == ProviderKind.NATIVE
    assert r.provider_id == "terminal"
    # Composio not connected, but resolver still knows the capability exists
    # via the native skill; external-only caps fall through gracefully.
    assert isinstance(r.to_dict()["available"], bool)


class _DummySkill:
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def manifest(self):  # type: ignore[no-untyped-def]
        class _M:
            name = self._name

        return _M()
