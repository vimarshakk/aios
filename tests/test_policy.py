"""Tests for aios.security.policy — approval & policy engine."""

from __future__ import annotations

from aios.agents.capability_catalog import CapabilityCatalog
from aios.agents.permissions import Permission
from aios.security.policy import (
    ApprovalDecision,
    ApprovalLevel,
    PolicyEngine,
    PolicyRule,
)
from aios.security.policy.levels import FORBIDDEN_PERMISSIONS, SENSITIVE_PERMISSIONS


class TestApprovalLevels:
    def test_level_values(self) -> None:
        assert ApprovalLevel.ALLOW.value == "allow"
        assert ApprovalLevel.ASK_ONCE.value == "ask_once"
        assert ApprovalLevel.ASK_ALWAYS.value == "ask_always"
        assert ApprovalLevel.DENY.value == "deny"

    def test_str_enum_comparison(self) -> None:
        assert ApprovalLevel.ASK_ONCE == "ask_once"
        assert ApprovalLevel.ALLOW != ApprovalLevel.ASK_ONCE


class TestPolicyRule:
    def test_applies_to(self) -> None:
        rule = PolicyRule(name="rw", matches=("filesystem.write",), level="ask_always")
        assert rule.applies_to("filesystem.write")
        assert not rule.applies_to("filesystem.read")


class TestPolicyEngine:
    def test_safe_action_allows(self) -> None:
        engine = PolicyEngine()
        dec = engine.evaluate(permissions=[Permission.FILESYSTEM_READ])
        assert dec.level == ApprovalLevel.ALLOW
        assert not dec.denied
        assert not dec.requires_approval

    def test_sensitive_permission_asks_once(self) -> None:
        engine = PolicyEngine()
        dec = engine.evaluate(permissions=[Permission.PROCESS_EXEC])
        assert dec.level == ApprovalLevel.ASK_ONCE
        assert dec.requires_approval

    def test_forbidden_permission_denies(self) -> None:
        engine = PolicyEngine()
        dec = engine.evaluate(permissions=list(FORBIDDEN_PERMISSIONS)[:1])
        assert dec.denied
        assert dec.level == ApprovalLevel.DENY

    def test_capability_scope_privileged(self) -> None:
        catalog = CapabilityCatalog()
        engine = PolicyEngine(catalog=catalog)
        # terminal.exec is privileged in the seeded catalog
        dec = engine.evaluate(capabilities=["terminal.exec"])
        assert dec.level == ApprovalLevel.ASK_ALWAYS

    def test_explicit_rule_overrides(self) -> None:
        engine = PolicyEngine(
            rules=[
                PolicyRule(
                    name="lockdown",
                    matches=("filesystem.read",),
                    level="ask_always",
                    priority=10,
                )
            ]
        )
        dec = engine.evaluate(permissions=[Permission.FILESYSTEM_READ])
        assert dec.level == ApprovalLevel.ASK_ALWAYS
        assert "lockdown" in dec.matched_rules

    def test_manifest_approval_floor(self) -> None:
        engine = PolicyEngine()
        dec = engine.evaluate(
            permissions=[Permission.FILESYSTEM_READ],
            manifest_approval="ask_once",
        )
        assert dec.level == ApprovalLevel.ASK_ONCE

    def test_rule_priority_wins(self) -> None:
        engine = PolicyEngine(
            rules=[
                PolicyRule(name="low", matches=("x",), level="ask_once", priority=1),
                PolicyRule(name="high", matches=("x",), level="ask_always", priority=99),
            ]
        )
        dec = engine.evaluate(capabilities=["x"])
        assert dec.level == ApprovalLevel.ASK_ALWAYS
        assert dec.matched_rules == ("high",)

    def test_add_rule_resorts(self) -> None:
        engine = PolicyEngine()
        engine.add_rule(
            PolicyRule(name="later", matches=("y",), level="ask_always", priority=5)
        )
        dec = engine.evaluate(capabilities=["y"])
        assert dec.level == ApprovalLevel.ASK_ALWAYS

    def test_sensitive_constants(self) -> None:
        assert Permission.PROCESS_EXEC in SENSITIVE_PERMISSIONS
        assert "system.shutdown" in FORBIDDEN_PERMISSIONS


class TestApprovalDecision:
    def test_requires_approval_property(self) -> None:
        d = ApprovalDecision(level=ApprovalLevel.ASK_ONCE)
        assert d.requires_approval
        d2 = ApprovalDecision(level=ApprovalLevel.ALLOW)
        assert not d2.requires_approval
        d3 = ApprovalDecision(level=ApprovalLevel.DENY, denied=True)
        assert not d3.requires_approval
