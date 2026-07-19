"""Tests for the permissions model — Permission, PermissionSet, PermissionChecker."""

import pytest

from aios.agents.permissions import (
    Permission,
    PermissionChecker,
    PermissionRequest,
    PermissionResult,
    PermissionSet,
)

# ---------------------------------------------------------------------------
# Permission constants
# ---------------------------------------------------------------------------


class TestPermission:
    def test_constants(self) -> None:
        assert Permission.FILESYSTEM_READ == "filesystem.read"
        assert Permission.FILESYSTEM_WRITE == "filesystem.write"
        assert Permission.NETWORK_HTTP == "network.http"
        assert Permission.NETWORK_TCP == "network.tcp"
        assert Permission.DESKTOP_MOUSE == "desktop.mouse"
        assert Permission.DESKTOP_KEYBOARD == "desktop.keyboard"
        assert Permission.PROCESS_EXEC == "process.exec"
        assert Permission.DATABASE_READ == "database.read"
        assert Permission.DATABASE_WRITE == "database.write"
        assert Permission.VOICE_RECORD == "voice.record"
        assert Permission.SCREEN_CAPTURE == "screen.capture"


# ---------------------------------------------------------------------------
# PermissionSet
# ---------------------------------------------------------------------------


class TestPermissionSet:
    def test_empty(self) -> None:
        ps = PermissionSet()
        assert len(ps) == 0
        assert ps.granted() == frozenset()

    def test_has(self) -> None:
        ps = PermissionSet(["a", "b", "c"])
        assert ps.has("a") is True
        assert ps.has("d") is False

    def test_has_all(self) -> None:
        ps = PermissionSet(["a", "b", "c"])
        assert ps.has_all(["a", "b"]) is True
        assert ps.has_all(["a", "x"]) is False

    def test_missing(self) -> None:
        ps = PermissionSet(["a", "b"])
        assert ps.missing(["a", "b", "c"]) == ["c"]
        assert ps.missing(["a"]) == []

    def test_contains(self) -> None:
        ps = PermissionSet(["x"])
        assert "x" in ps
        assert "y" not in ps

    def test_equality(self) -> None:
        a = PermissionSet(["a", "b"])
        b = PermissionSet(["b", "a"])
        assert a == b
        c = PermissionSet(["a"])
        assert a != c

    def test_repr(self) -> None:
        ps = PermissionSet(["b", "a"])
        r = repr(ps)
        assert "PermissionSet" in r
        assert "a" in r

    def test_not_equal_to_non_set(self) -> None:
        ps = PermissionSet(["a"])
        assert ps != "not a set"  # type: ignore[comparison-overlap]


# ---------------------------------------------------------------------------
# PermissionRequest / PermissionResult
# ---------------------------------------------------------------------------


class TestPermissionRequest:
    def test_construction(self) -> None:
        req = PermissionRequest(
            permissions=("filesystem.read",),
            reason="Need to read config",
            source="config_tool",
        )
        assert req.permissions == ("filesystem.read",)
        assert req.reason == "Need to read config"
        assert req.source == "config_tool"

    def test_frozen(self) -> None:
        req = PermissionRequest(permissions=("a",))
        with pytest.raises(AttributeError):
            req.reason = "x"  # type: ignore[misc]


class TestPermissionResult:
    def test_approved_when_no_denied(self) -> None:
        res = PermissionResult(granted=("a", "b"), denied=())
        assert res.approved is True

    def test_not_approved_when_denied(self) -> None:
        res = PermissionResult(granted=("a",), denied=("b",))
        assert res.approved is False


# ---------------------------------------------------------------------------
# PermissionChecker
# ---------------------------------------------------------------------------


class TestPermissionChecker:
    def test_check_all_granted(self) -> None:
        checker = PermissionChecker(granted=PermissionSet(["a", "b", "c"]))
        assert checker.check(["a", "b"]) is True

    def test_check_missing(self) -> None:
        checker = PermissionChecker(granted=PermissionSet(["a"]))
        assert checker.check(["a", "b"]) is False

    def test_check_empty_required(self) -> None:
        checker = PermissionChecker(granted=PermissionSet())
        assert checker.check([]) is True

    def test_enforce_all_granted(self) -> None:
        checker = PermissionChecker(granted=PermissionSet(["a", "b"]))
        result = checker.enforce(["a", "b"])
        assert result.approved is True
        assert result.granted == ("a", "b")
        assert result.denied == ()

    def test_enforce_with_denied(self) -> None:
        checker = PermissionChecker(granted=PermissionSet(["a"]))
        result = checker.enforce(["a", "b", "c"])
        assert result.approved is False
        assert result.granted == ("a",)
        assert result.denied == ("b", "c")

    def test_enforce_tool_object(self) -> None:
        class FakeTool:
            permissions = ("network.http", "filesystem.read")

        checker = PermissionChecker(
            granted=PermissionSet(["network.http", "filesystem.read"])
        )
        assert checker.check_tool(FakeTool()) is True
        result = checker.enforce_tool(FakeTool())
        assert result.approved is True

    def test_enforce_tool_no_permissions(self) -> None:
        class NoPermsTool:
            pass

        checker = PermissionChecker(granted=PermissionSet())
        assert checker.check_tool(NoPermsTool()) is True
        result = checker.enforce_tool(NoPermsTool())
        assert result.approved is True

    def test_enforce_tool_missing_permissions(self) -> None:
        class ShellTool:
            permissions = ("process.exec", "filesystem.read")

        checker = PermissionChecker(granted=PermissionSet(["process.exec"]))
        assert checker.check_tool(ShellTool()) is False
        result = checker.enforce_tool(ShellTool())
        assert result.approved is False
        assert "filesystem.read" in result.denied

    def test_grant(self) -> None:
        checker = PermissionChecker(granted=PermissionSet())
        checker.grant("a", "b")
        assert checker.check(["a", "b"]) is True

    def test_revoke(self) -> None:
        checker = PermissionChecker(granted=PermissionSet(["a", "b"]))
        checker.revoke("a")
        assert checker.check(["a"]) is False
        assert checker.check(["b"]) is True

    def test_on_request_callback_approved(self) -> None:
        def approve(req: PermissionRequest) -> PermissionResult:
            return PermissionResult(granted=req.permissions, denied=())

        checker = PermissionChecker(
            granted=PermissionSet(),
            on_request=approve,
        )
        result = checker.enforce(["network.http"])
        assert result.approved is True
        assert "network.http" in result.granted

    def test_on_request_callback_partial(self) -> None:
        def partial(req: PermissionRequest) -> PermissionResult:
            granted = [p for p in req.permissions if "read" in p]
            denied = [p for p in req.permissions if "read" not in p]
            return PermissionResult(
                granted=tuple(granted), denied=tuple(denied)
            )

        checker = PermissionChecker(
            granted=PermissionSet(),
            on_request=partial,
        )
        result = checker.enforce(["filesystem.read", "filesystem.write"])
        assert "filesystem.read" in result.granted
        assert "filesystem.write" in result.denied

    def test_on_request_callback_denied(self) -> None:
        def deny_all(req: PermissionRequest) -> PermissionResult:
            return PermissionResult(granted=(), denied=req.permissions)

        checker = PermissionChecker(
            granted=PermissionSet(),
            on_request=deny_all,
        )
        result = checker.enforce(["network.http"])
        assert result.approved is False
        assert result.denied == ("network.http",)

    def test_grant_merges_with_existing(self) -> None:
        checker = PermissionChecker(granted=PermissionSet(["a"]))
        checker.grant("b", "c")
        assert checker.check(["a", "b", "c"]) is True
        assert checker.check(["a"]) is True

    def test_revoke_nonexistent_is_noop(self) -> None:
        checker = PermissionChecker(granted=PermissionSet(["a"]))
        checker.revoke("x")
        assert checker.check(["a"]) is True


# ---------------------------------------------------------------------------
# Integration with BaseTool
# ---------------------------------------------------------------------------


class TestBaseToolPermissions:
    def test_base_tool_has_permissions_attr(self) -> None:
        from aios.agents.tools import BaseTool, ToolSpec
        from aios.agents.types import ToolResult

        class MyTool(BaseTool):
            spec = ToolSpec(name="mytool", description="test")
            permissions = (Permission.NETWORK_HTTP, Permission.FILESYSTEM_READ)

            async def execute(self, **kw: object) -> ToolResult:
                return ToolResult(output="ok")

        tool = MyTool()
        checker = PermissionChecker(granted=PermissionSet([Permission.NETWORK_HTTP]))
        assert checker.check_tool(tool) is False
        result = checker.enforce_tool(tool)
        assert result.approved is False
        assert Permission.FILESYSTEM_READ in result.denied

    def test_base_tool_no_permissions(self) -> None:
        from aios.agents.tools import BaseTool, ToolSpec
        from aios.agents.types import ToolResult

        class SimpleTool(BaseTool):
            spec = ToolSpec(name="simple", description="test")

            async def execute(self, **kw: object) -> ToolResult:
                return ToolResult(output="ok")

        tool = SimpleTool()
        checker = PermissionChecker(granted=PermissionSet())
        assert checker.check_tool(tool) is True
