"""Tests for aios.agents.capability_catalog — hierarchical capability taxonomy."""

from __future__ import annotations

import pytest

from aios.agents.capability_catalog import (
    CapabilityCatalog,
    CapabilityNode,
    CapabilityScope,
)


class TestCapabilityCatalogBasics:
    def test_seeded_capabilities_present(self) -> None:
        catalog = CapabilityCatalog()
        assert catalog.has("filesystem")
        assert catalog.has("filesystem.write")
        assert catalog.has("browser.navigate")
        assert catalog.has("git.push")

    def test_get_returns_node(self) -> None:
        catalog = CapabilityCatalog()
        node = catalog.get("filesystem.write")
        assert isinstance(node, CapabilityNode)
        assert node.name == "filesystem.write"
        assert node.parent == "filesystem"

    def test_get_missing_raises(self) -> None:
        catalog = CapabilityCatalog()
        with pytest.raises(KeyError, match="No capability"):
            catalog.get("nonexistent.thing")

    def test_has_false_for_missing(self) -> None:
        catalog = CapabilityCatalog()
        assert catalog.has("nope.nope") is False

    def test_roots(self) -> None:
        catalog = CapabilityCatalog()
        roots = {r.name for r in catalog.roots()}
        assert "filesystem" in roots
        assert "browser" in roots
        assert "git" in roots
        assert "docker" in roots

    def test_leaves(self) -> None:
        catalog = CapabilityCatalog()
        leaf_names = {leaf.name for leaf in catalog.leaves()}
        assert "filesystem.write" in leaf_names
        assert "git.push" in leaf_names
        assert "filesystem" not in leaf_names  # it's a domain, not a leaf

    def test_children(self) -> None:
        catalog = CapabilityCatalog()
        children = {c.name for c in catalog.children("filesystem")}
        assert children == {
            "filesystem.read",
            "filesystem.write",
            "filesystem.search",
            "filesystem.delete",
        }

    def test_parents_chain(self) -> None:
        catalog = CapabilityCatalog()
        parents = [p.name for p in catalog.parents("filesystem.write")]
        assert parents == ["filesystem"]

    def test_domain_property(self) -> None:
        catalog = CapabilityCatalog()
        node = catalog.get("git.push")
        assert node.domain == "git"

    def test_is_leaf_property(self) -> None:
        catalog = CapabilityCatalog()
        assert catalog.get("git.push").is_leaf is True
        assert catalog.get("git").is_leaf is False


class TestCapabilityCatalogRegistration:
    def test_register_custom_leaf(self) -> None:
        catalog = CapabilityCatalog()
        node = catalog.register(
            "slack.send",
            description="Send a Slack message",
            parent=None,
            required_permission=None,
            scope=CapabilityScope.INTERACTIVE,
            tags=("messaging",),
        )
        assert catalog.has("slack.send")
        assert node.parent is None
        assert node.tags == ("messaging",)

    def test_register_child_requires_parent(self) -> None:
        catalog = CapabilityCatalog()
        with pytest.raises(ValueError, match="Parent capability"):
            catalog.register("x.y", parent="nonexistent.parent")

    def test_register_duplicate_raises(self) -> None:
        catalog = CapabilityCatalog()
        with pytest.raises(ValueError, match="already registered"):
            catalog.register("filesystem.write")

    def test_register_with_parent(self) -> None:
        catalog = CapabilityCatalog()
        catalog.register("figma", description="Figma access")
        catalog.register("figma.read", parent="figma", description="Read Figma file")
        catalog.register("figma.extract", parent="figma", description="Extract nodes")
        children = {c.name for c in catalog.children("figma")}
        assert children == {"figma.read", "figma.extract"}


class TestCapabilityCatalogQueries:
    def test_by_permission(self) -> None:
        catalog = CapabilityCatalog()
        caps = {c.name for c in catalog.by_permission("FILESYSTEM_WRITE")}
        assert "filesystem.write" in caps
        assert "filesystem.delete" in caps
        assert "filesystem.read" not in caps  # uses FILESYSTEM_READ

    def test_by_scope(self) -> None:
        catalog = CapabilityCatalog()
        destructive = {c.name for c in catalog.by_scope(CapabilityScope.DESTRUCTIVE)}
        assert "filesystem.write" in destructive
        assert "filesystem.delete" in destructive
        privileged = {c.name for c in catalog.by_scope(CapabilityScope.PRIVILEGED)}
        assert "git.push" in privileged
        assert "terminal.exec" in privileged

    def test_by_tag(self) -> None:
        catalog = CapabilityCatalog()
        web = {c.name for c in catalog.by_tag("web")}
        assert "browser.navigate" in web
        assert "network.http" in web

    def test_resolve_subtree(self) -> None:
        catalog = CapabilityCatalog()
        resolved = {c.name for c in catalog.resolve("filesystem")}
        assert resolved == {
            "filesystem",
            "filesystem.read",
            "filesystem.write",
            "filesystem.search",
            "filesystem.delete",
        }

    def test_all_returns_all(self) -> None:
        catalog = CapabilityCatalog()
        all_caps = catalog.all()
        assert len(all_caps) > 20
        assert all(isinstance(c, CapabilityNode) for c in all_caps)


class TestCapabilityCatalogClear:
    def test_clear_resets_to_defaults(self) -> None:
        catalog = CapabilityCatalog()
        catalog.clear()
        # Defaults are re-seeded
        assert catalog.has("filesystem.write")
        assert len(catalog.all()) > 20


class TestCapabilityScope:
    def test_scope_values(self) -> None:
        assert CapabilityScope.SAFE.value == "safe"
        assert CapabilityScope.DESTRUCTIVE.value == "destructive"
        assert CapabilityScope.PRIVILEGED.value == "privileged"
        assert CapabilityScope.INTERACTIVE.value == "interactive"


class TestCapabilityHierarchy:
    def test_subtree_includes_descendants(self) -> None:
        catalog = CapabilityCatalog()
        names = {n.name for n in catalog.subtree("filesystem")}
        assert names == {
            "filesystem",
            "filesystem.read",
            "filesystem.write",
            "filesystem.search",
            "filesystem.delete",
        }

    def test_depth(self) -> None:
        catalog = CapabilityCatalog()
        assert catalog.depth("filesystem") == 0
        assert catalog.depth("filesystem.write") == 1

    def test_render_tree(self) -> None:
        catalog = CapabilityCatalog()
        tree = catalog.render_tree("browser")
        assert tree.startswith("browser")
        assert "browser.navigate" in tree
        assert "filesystem" not in tree

    def test_merge_combines_catalogs(self) -> None:
        base = CapabilityCatalog()
        other = CapabilityCatalog()
        other.register(
            "custom", description="A custom domain"
        )
        other.register(
            "custom.action", parent="custom", description="Custom action"
        )
        base.merge(other)
        assert base.has("custom.action")
        assert base.get("custom.action").parent == "custom"

    def test_merge_skips_duplicates(self) -> None:
        base = CapabilityCatalog()
        other = CapabilityCatalog()
        # Add exactly one new (non-default) node to `other`.
        other.register("custom", description="A custom domain")
        before = len(base.all())
        base.merge(other)
        # After merge, only the new 'custom' domain should be added.
        assert len(base.all()) == before + 1
        assert base.has("custom")
