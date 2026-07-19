"""Comprehensive tests for M2.3 — Plugin Marketplace, Versions, Dependencies, PermissionPolicy."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from aios.plugins.dependencies import (
    CircularDependencyError,
    DependencyResolver,
    MissingDependencyError,
)
from aios.plugins.marketplace import (
    MarketplaceEntry,
    MarketplaceNotFoundError,
    PluginMarketplace,
    VersionConflictError,
)
from aios.plugins.sandbox import PermissionPolicy, PluginSandbox, SandboxConfig
from aios.plugins.versions import SemVer, VersionRange, is_compatible

if TYPE_CHECKING:
    from pathlib import Path

# ===================================================================
# SemVer
# ===================================================================


class TestSemVer:
    def test_parse_basic(self) -> None:
        v = SemVer.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_with_v_prefix(self) -> None:
        v = SemVer.parse("v2.0.1")
        assert v.major == 2
        assert v.minor == 0
        assert v.patch == 1

    def test_parse_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid semver"):
            SemVer.parse("not-a-version")

    def test_parse_partial(self) -> None:
        with pytest.raises(ValueError, match="Invalid semver"):
            SemVer.parse("1.2")

    def test_str(self) -> None:
        assert str(SemVer(1, 2, 3)) == "1.2.3"

    def test_comparison_lt(self) -> None:
        assert SemVer(1, 0, 0) < SemVer(2, 0, 0)
        assert SemVer(1, 0, 0) < SemVer(1, 1, 0)
        assert SemVer(1, 0, 0) < SemVer(1, 0, 1)

    def test_comparison_gt(self) -> None:
        assert SemVer(2, 0, 0) > SemVer(1, 0, 0)
        assert SemVer(1, 1, 0) > SemVer(1, 0, 0)

    def test_comparison_eq(self) -> None:
        assert SemVer(1, 2, 3) == SemVer(1, 2, 3)

    def test_comparison_le(self) -> None:
        assert SemVer(1, 0, 0) <= SemVer(1, 0, 0)
        assert SemVer(1, 0, 0) <= SemVer(1, 0, 1)

    def test_comparison_ge(self) -> None:
        assert SemVer(2, 0, 0) >= SemVer(1, 0, 0)
        assert SemVer(1, 0, 0) >= SemVer(1, 0, 0)

    def test_frozen(self) -> None:
        v = SemVer(1, 2, 3)
        with pytest.raises(AttributeError):
            v.major = 2  # type: ignore[misc]


# ===================================================================
# VersionRange
# ===================================================================


class TestVersionRange:
    def test_exact_match(self) -> None:
        r = VersionRange("1.2.3")
        assert r.matches(SemVer(1, 2, 3))
        assert not r.matches(SemVer(1, 2, 4))

    def test_caret_range(self) -> None:
        r = VersionRange("^1.2.3")
        assert r.matches(SemVer(1, 2, 3))
        assert r.matches(SemVer(1, 9, 9))
        assert not r.matches(SemVer(2, 0, 0))
        assert not r.matches(SemVer(1, 2, 2))

    def test_tilde_range(self) -> None:
        r = VersionRange("~1.3.0")
        assert r.matches(SemVer(1, 3, 0))
        assert r.matches(SemVer(1, 3, 5))
        assert not r.matches(SemVer(1, 4, 0))
        assert not r.matches(SemVer(2, 3, 0))

    def test_space_range(self) -> None:
        r = VersionRange(">=1.0.0 <2.0.0")
        assert r.matches(SemVer(1, 0, 0))
        assert r.matches(SemVer(1, 9, 9))
        assert not r.matches(SemVer(2, 0, 0))
        assert not r.matches(SemVer(0, 9, 9))

    def test_is_compatible(self) -> None:
        assert is_compatible("1.2.3", "^1.0.0")
        assert is_compatible("1.9.9", "^1.0.0")
        assert not is_compatible("2.0.0", "^1.0.0")


# ===================================================================
# MarketplaceEntry
# ===================================================================


class TestMarketplaceEntry:
    def test_from_manifest(self) -> None:
        from aios.plugins.manifest import PluginManifest, ToolSpec

        m = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            description="A test plugin",
            author="test",
            permissions=("network.http",),
            tools=(ToolSpec(name="do_thing"),),
        )
        entry = MarketplaceEntry.from_manifest(m)
        assert entry.name == "test-plugin"
        assert entry.version == "1.0.0"
        assert entry.author == "test"
        assert entry.permissions == ("network.http",)
        assert len(entry.tools) == 1
        assert entry.published_at > 0

    def test_to_dict_round_trip(self) -> None:
        entry = MarketplaceEntry(
            name="rt",
            version="1.0.0",
            description="Round trip",
            author="a",
            permissions=("a",),
            tags=("tag1",),
        )
        d = entry.to_dict()
        restored = MarketplaceEntry.from_dict(d)
        assert restored.name == "rt"
        assert restored.version == "1.0.0"
        assert restored.permissions == ("a",)
        assert restored.tags == ("tag1",)

    def test_from_dict_minimal(self) -> None:
        entry = MarketplaceEntry.from_dict({"name": "min"})
        assert entry.name == "min"
        assert entry.version == "0.0.0"
        assert entry.tools == ()


# ===================================================================
# PluginMarketplace
# ===================================================================


class TestPluginMarketplace:
    def test_publish_and_get(self) -> None:
        mp = PluginMarketplace()
        entry = MarketplaceEntry(name="alpha", version="1.0.0")
        mp.publish(entry)
        got = mp.get("alpha")
        assert got.name == "alpha"
        assert got.version == "1.0.0"

    def test_publish_update_version(self) -> None:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(name="beta", version="1.0.0"))
        mp.publish(MarketplaceEntry(name="beta", version="1.1.0"))
        assert mp.get("beta").version == "1.1.0"

    def test_publish_rejects_lower_version(self) -> None:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(name="gamma", version="2.0.0"))
        with pytest.raises(VersionConflictError, match="not greater than"):
            mp.publish(MarketplaceEntry(name="gamma", version="1.0.0"))

    def test_publish_rejects_same_version(self) -> None:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(name="delta", version="1.0.0"))
        with pytest.raises(VersionConflictError):
            mp.publish(MarketplaceEntry(name="delta", version="1.0.0"))

    def test_get_not_found(self) -> None:
        mp = PluginMarketplace()
        with pytest.raises(MarketplaceNotFoundError):
            mp.get("nonexistent")

    def test_search_by_name(self) -> None:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(
            name="github", version="1.0.0", description="GitHub integration",
        ))
        mp.publish(MarketplaceEntry(
            name="gitlab", version="1.0.0", description="GitLab integration",
        ))
        mp.publish(MarketplaceEntry(
            name="slack", version="1.0.0", description="Slack notifications",
        ))
        results = mp.search(query="git")
        names = [e.name for e in results]
        assert "github" in names
        assert "gitlab" in names
        assert "slack" not in names

    def test_search_by_tags(self) -> None:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(name="a", version="1.0.0", tags=("ai", "llm")))
        mp.publish(MarketplaceEntry(name="b", version="1.0.0", tags=("ai",)))
        mp.publish(MarketplaceEntry(name="c", version="1.0.0", tags=("dev",)))
        results = mp.search(tags=("llm",))
        assert len(results) == 1
        assert results[0].name == "a"

    def test_list_all_sorted_by_downloads(self) -> None:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(name="a", version="1.0.0", downloads=10))
        mp.publish(MarketplaceEntry(name="b", version="1.0.0", downloads=100))
        mp.publish(MarketplaceEntry(name="c", version="1.0.0", downloads=50))
        all_entries = mp.list_all()
        assert [e.name for e in all_entries] == ["b", "c", "a"]

    def test_remove(self) -> None:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(name="rm", version="1.0.0"))
        mp.remove("rm")
        with pytest.raises(MarketplaceNotFoundError):
            mp.get("rm")

    def test_remove_not_found(self) -> None:
        mp = PluginMarketplace()
        with pytest.raises(MarketplaceNotFoundError):
            mp.remove("ghost")

    def test_install_uninstall(self) -> None:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(name="inst", version="1.0.0"))
        mp.install("inst")
        assert mp.is_installed("inst")
        assert mp.installed_version("inst") == "1.0.0"
        mp.uninstall("inst")
        assert not mp.is_installed("inst")
        assert mp.installed_version("inst") is None

    def test_install_increments_downloads(self) -> None:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(name="pop", version="1.0.0", downloads=5))
        mp.install("pop")
        assert mp.get("pop").downloads == 6

    def test_install_not_found(self) -> None:
        mp = PluginMarketplace()
        with pytest.raises(MarketplaceNotFoundError):
            mp.install("ghost")

    def test_uninstall_not_installed(self) -> None:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(name="x", version="1.0.0"))
        with pytest.raises(MarketplaceNotFoundError):
            mp.uninstall("x")

    def test_list_installed(self) -> None:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(name="a", version="1.0.0"))
        mp.publish(MarketplaceEntry(name="b", version="1.0.0"))
        mp.install("a")
        installed = mp.list_installed()
        assert len(installed) == 1
        assert installed[0].name == "a"

    def test_check_update(self) -> None:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(name="upd", version="2.0.0"))
        assert mp.check_update("upd", "1.0.0") == "2.0.0"
        assert mp.check_update("upd", "2.0.0") is None
        assert mp.check_update("upd", "3.0.0") is None

    def test_check_update_not_in_marketplace(self) -> None:
        mp = PluginMarketplace()
        assert mp.check_update("ghost", "1.0.0") is None


# ===================================================================
# PluginMarketplace — persistence
# ===================================================================


class TestMarketplacePersistence:
    def test_save_and_load(self, tmp_path: Path) -> None:
        storage = tmp_path / "market.jsonl"
        mp1 = PluginMarketplace(storage_path=str(storage))
        mp1.publish(MarketplaceEntry(name="p1", version="1.0.0"))
        mp1.publish(MarketplaceEntry(name="p2", version="2.0.0"))

        mp2 = PluginMarketplace(storage_path=str(storage))
        assert mp2.get("p1").version == "1.0.0"
        assert mp2.get("p2").version == "2.0.0"

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        mp = PluginMarketplace(storage_path=str(tmp_path / "nope.jsonl"))
        assert mp.list_all() == []


# ===================================================================
# DependencyResolver
# ===================================================================


class TestDependencyResolver:
    def _make_marketplace(self) -> PluginMarketplace:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(name="core", version="1.0.0"))
        mp.publish(MarketplaceEntry(
            name="addon",
            version="1.0.0",
            dependencies={"core": "^1.0.0"},
        ))
        mp.publish(MarketplaceEntry(
            name="plugin-a",
            version="1.0.0",
            dependencies={"core": "^1.0.0", "addon": "^1.0.0"},
        ))
        return mp

    def test_get_dependencies(self) -> None:
        mp = self._make_marketplace()
        dr = DependencyResolver(mp)
        deps = dr.get_dependencies("addon")
        assert deps == {"core": "^1.0.0"}

    def test_get_dependencies_no_deps(self) -> None:
        mp = self._make_marketplace()
        dr = DependencyResolver(mp)
        deps = dr.get_dependencies("core")
        assert deps == {}

    def test_validate_simple(self) -> None:
        mp = self._make_marketplace()
        dr = DependencyResolver(mp)
        resolved = dr.validate("addon")
        assert len(resolved) == 2
        names = [r.name for r in resolved]
        assert "core" in names
        assert "addon" in names

    def test_validate_chain(self) -> None:
        mp = self._make_marketplace()
        dr = DependencyResolver(mp)
        resolved = dr.validate("plugin-a")
        assert len(resolved) == 3
        names = [r.name for r in resolved]
        assert names.index("core") < names.index("addon")
        assert names.index("addon") < names.index("plugin-a")

    def test_topological_sort(self) -> None:
        mp = self._make_marketplace()
        dr = DependencyResolver(mp)
        order = dr.topological_sort(["addon", "core"])
        assert order.index("core") < order.index("addon")

    def test_topological_sort_chain(self) -> None:
        mp = self._make_marketplace()
        dr = DependencyResolver(mp)
        order = dr.topological_sort(["plugin-a"])
        assert order.index("core") < order.index("addon")
        assert order.index("addon") < order.index("plugin-a")

    def test_missing_dependency(self) -> None:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(
            name="orphan",
            version="1.0.0",
            dependencies={"nonexistent": "^1.0.0"},
        ))
        dr = DependencyResolver(mp)
        with pytest.raises(MissingDependencyError):
            dr.validate("orphan")

    def test_circular_dependency(self) -> None:
        mp = PluginMarketplace()
        mp.publish(MarketplaceEntry(
            name="circ-a",
            version="1.0.0",
            dependencies={"circ-b": "^1.0.0"},
        ))
        mp.publish(MarketplaceEntry(
            name="circ-b",
            version="1.0.0",
            dependencies={"circ-a": "^1.0.0"},
        ))
        dr = DependencyResolver(mp)
        with pytest.raises(CircularDependencyError):
            dr.validate("circ-a")


# ===================================================================
# PermissionPolicy
# ===================================================================


class TestPermissionPolicy:
    def test_classify_safe(self) -> None:
        pp = PermissionPolicy()
        assert pp.classify("memory.read") == "safe"
        assert pp.classify("workflow.read") == "safe"

    def test_classify_approval(self) -> None:
        pp = PermissionPolicy()
        assert pp.classify("network.http") == "approval"
        assert pp.classify("filesystem.read") == "approval"

    def test_classify_denied(self) -> None:
        pp = PermissionPolicy()
        assert pp.classify("filesystem.write") == "denied"
        assert pp.classify("system.exec") == "denied"
        assert pp.classify("admin.all") == "denied"

    def test_is_allowed_safe(self) -> None:
        pp = PermissionPolicy()
        assert pp.is_allowed("memory.read") is True

    def test_is_allowed_approval_no_approved(self) -> None:
        pp = PermissionPolicy()
        assert pp.is_allowed("network.http") is False

    def test_is_allowed_approval_approved(self) -> None:
        pp = PermissionPolicy()
        assert pp.is_allowed("network.http", frozenset({"network.http"})) is True

    def test_is_allowed_denied_always(self) -> None:
        pp = PermissionPolicy()
        assert pp.is_allowed("system.exec", frozenset({"system.exec"})) is False

    def test_check_manifest_all_safe(self) -> None:
        pp = PermissionPolicy()
        allowed, denied = pp.check_manifest(("memory.read", "workflow.read"))
        assert allowed == ["memory.read", "workflow.read"]
        assert denied == []

    def test_check_manifest_mixed(self) -> None:
        pp = PermissionPolicy()
        allowed, denied = pp.check_manifest(
            ("memory.read", "network.http", "system.exec")
        )
        assert "memory.read" in allowed
        # network.http requires approval — goes to denied without approved set
        assert "network.http" in denied
        assert "system.exec" in denied

    def test_check_manifest_all_denied(self) -> None:
        pp = PermissionPolicy()
        allowed, denied = pp.check_manifest(("system.exec", "admin.all"))
        assert allowed == []
        assert denied == ["system.exec", "admin.all"]


# ===================================================================
# PluginSandbox enhanced
# ===================================================================


class TestPluginSandboxEnhanced:
    def test_permission_policy_integration(self) -> None:
        sb = PluginSandbox(SandboxConfig(allowed_permissions=("memory.read",)))
        assert sb.check_permission("memory.read") is True
        # sandbox restricts to allowed_permissions only
        assert sb.check_permission("filesystem.write") is False

    def test_policy_with_sandbox(self) -> None:
        pp = PermissionPolicy()
        sb = PluginSandbox(SandboxConfig(allowed_permissions=("memory.read",)))
        manifest_perms = ("memory.read", "network.http", "system.exec")
        allowed, _blocked = sb.filter_permissions(list(manifest_perms))
        _policy_allowed, policy_denied = pp.check_manifest(manifest_perms)
        # Sandbox says memory.read is allowed, network.http is allowed (sandbox is permissive)
        assert "memory.read" in allowed
        # Policy says system.exec is denied
        assert "system.exec" in policy_denied
