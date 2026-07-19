"""Capability Catalog — hierarchical taxonomy of platform capabilities.

This is the **single source of truth** for capabilities in AIOS. It is distinct
from :class:`aios.agents.registry.CapabilityRegistry` (which stores arbitrary
registered objects). The catalog defines *what capabilities exist*, their
hierarchy, and which :class:`~aios.agents.permissions.Permission` (frozen)
authorizes each one.

Layering (see ADR-0019)::

    Skill ─requires→ Capability (catalog) ─authorized-by→ Permission (frozen)
                                    ↑
                            implemented-by Connector

Capabilities use dotted names forming a hierarchy::

    filesystem
      filesystem.read
      filesystem.write
      filesystem.search
      filesystem.delete
    browser
      browser.navigate
      browser.extract
    git
      git.commit
      git.push
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CapabilityScope(StrEnum):
    """Risk scope of a capability, used to suggest default approval levels."""

    SAFE = "safe"
    INTERACTIVE = "interactive"
    DESTRUCTIVE = "destructive"
    PRIVILEGED = "privileged"


@dataclass(frozen=True)
class CapabilityNode:
    """A node in the capability taxonomy.

    Attributes:
        name: Dot-separated capability name (e.g. ``filesystem.write``).
        description: Human-readable description.
        parent: Parent capability name, or ``None`` for a root domain.
        required_permission: Frozen :class:`Permission` that authorizes this.
        scope: Risk scope used to pick default approval level.
        tags: Freeform tags for grouping/filtering.
    """

    name: str
    description: str = ""
    parent: str | None = None
    required_permission: str | None = None
    scope: CapabilityScope = CapabilityScope.SAFE
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def domain(self) -> str:
        """Top-level domain (first dotted segment)."""
        return self.name.split(".", 1)[0]

    @property
    def is_leaf(self) -> bool:
        """Whether this node is a leaf (has no registered children)."""
        return self.name not in _CHILDREN


class CapabilityCatalog:
    """Hierarchical catalog of all platform capabilities.

    Usage::

        catalog = CapabilityCatalog()
        catalog.register(
            "filesystem.write",
            description="Write files",
            parent="filesystem",
            required_permission="FILESYSTEM_WRITE",
            scope=CapabilityScope.DESTRUCTIVE,
        )
        node = catalog.get("filesystem.write")
        children = catalog.children("filesystem")
        leaves = catalog.leaves()
    """

    def __init__(self) -> None:
        self._nodes: dict[str, CapabilityNode] = {}
        self._seed_defaults()

    # -- registration ------------------------------------------------------

    def register(
        self,
        name: str,
        *,
        description: str = "",
        parent: str | None = None,
        required_permission: str | None = None,
        scope: CapabilityScope = CapabilityScope.SAFE,
        tags: tuple[str, ...] | list[str] = (),
    ) -> CapabilityNode:
        """Register a capability node. Parent must exist unless it is a root."""
        if name in self._nodes:
            raise ValueError(f"Capability '{name}' already registered")
        if parent is not None and parent not in self._nodes:
            raise ValueError(f"Parent capability '{parent}' is not registered")
        node = CapabilityNode(
            name=name,
            description=description,
            parent=parent,
            required_permission=required_permission,
            scope=scope,
            tags=tuple(tags),
        )
        self._nodes[name] = node
        if parent is not None:
            _CHILDREN.setdefault(parent, []).append(name)
        return node

    # -- lookup ------------------------------------------------------------

    def get(self, name: str) -> CapabilityNode:
        """Return a capability node by name."""
        if name not in self._nodes:
            raise KeyError(f"No capability registered with name '{name}'")
        return self._nodes[name]

    def has(self, name: str) -> bool:
        """Whether a capability is registered."""
        return name in self._nodes

    def children(self, name: str) -> list[CapabilityNode]:
        """Return direct children of a capability."""
        return [self._nodes[c] for c in _CHILDREN.get(name, [])]

    def parents(self, name: str) -> list[CapabilityNode]:
        """Return ancestor chain from root down to (but excluding) ``name``."""
        chain: list[CapabilityNode] = []
        node = self._nodes.get(name)
        while node is not None and node.parent is not None:
            parent = self._nodes.get(node.parent)
            if parent is None:
                break
            chain.append(parent)
            node = parent
        chain.reverse()
        return chain

    def leaves(self) -> list[CapabilityNode]:
        """Return all leaf capabilities (no children)."""
        return [n for n in self._nodes.values() if n.is_leaf]

    def roots(self) -> list[CapabilityNode]:
        """Return all root domains (no parent)."""
        return [n for n in self._nodes.values() if n.parent is None]

    def all(self) -> list[CapabilityNode]:
        """Return all registered capability nodes."""
        return list(self._nodes.values())

    def by_permission(self, permission: str) -> list[CapabilityNode]:
        """Return capabilities authorized by a given frozen permission name."""
        return [
            n for n in self._nodes.values()
            if n.required_permission == permission
        ]

    def by_scope(self, scope: CapabilityScope) -> list[CapabilityNode]:
        """Return capabilities of a given risk scope."""
        return [n for n in self._nodes.values() if n.scope == scope]

    def by_tag(self, tag: str) -> list[CapabilityNode]:
        """Return capabilities carrying a given tag."""
        return [n for n in self._nodes.values() if tag in n.tags]

    def resolve(self, name: str) -> list[CapabilityNode]:
        """Resolve a capability (or domain) to itself plus all descendants.

        Useful for granting a whole subtree (e.g. ``filesystem`` → all fs caps).
        """
        result = [self._nodes[name]]
        for child in _CHILDREN.get(name, []):
            result.extend(self.resolve(child))
        return result

    def clear(self) -> None:
        """Remove all registered capabilities."""
        self._nodes.clear()
        _CHILDREN.clear()
        self._seed_defaults()

    # -- hierarchy helpers -------------------------------------------------

    def subtree(self, name: str) -> list[CapabilityNode]:
        """Return the node plus all of its transitive descendants (BFS order)."""
        if name not in self._nodes:
            raise KeyError(f"No capability registered with name '{name}'")
        ordered: list[CapabilityNode] = []
        queue = [name]
        seen: set[str] = set()
        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            ordered.append(self._nodes[current])
            queue.extend(_CHILDREN.get(current, []))
        return ordered

    def depth(self, name: str) -> int:
        """Return the depth of a node (root domain = 0)."""
        node = self._nodes.get(name)
        if node is None:
            raise KeyError(f"No capability registered with name '{name}'")
        level = 0
        while node.parent is not None:
            level += 1
            parent = self._nodes.get(node.parent)
            if parent is None:
                break
            node = parent
        return level

    def render_tree(self, root: str | None = None) -> str:
        """Render the taxonomy as an indented text tree (for discovery/CLI)."""
        roots = [root] if root is not None else [n.name for n in self.roots()]
        lines: list[str] = []

        def _walk(name: str, indent: int) -> None:
            node = self._nodes.get(name)
            if node is None:
                return
            lines.append(f"{'  ' * indent}{node.name}")
            for child in _CHILDREN.get(name, []):
                _walk(child, indent + 1)

        for r in roots:
            _walk(r, 0)
        return "\n".join(lines)

    def merge(self, other: CapabilityCatalog) -> None:
        """Merge another catalog's nodes into this one (skips duplicates)."""
        for node in other.all():
            if node.name in self._nodes:
                continue
            self.register(
                node.name,
                description=node.description,
                parent=node.parent,
                required_permission=node.required_permission,
                scope=node.scope,
                tags=node.tags,
            )

    # -- defaults ----------------------------------------------------------

    def _seed_defaults(self) -> None:
        """Seed the catalog with the canonical AIOS capability taxonomy.

        These are the capabilities referenced across the platform; connectors
        implement them and skills require them.
        """
        # Filesystem
        self.register("filesystem", description="Local filesystem access")
        self.register(
            "filesystem.read", parent="filesystem",
            description="Read files and directories",
            required_permission="FILESYSTEM_READ",
            scope=CapabilityScope.SAFE, tags=("io",),
        )
        self.register(
            "filesystem.write", parent="filesystem",
            description="Create or modify files",
            required_permission="FILESYSTEM_WRITE",
            scope=CapabilityScope.DESTRUCTIVE, tags=("io",),
        )
        self.register(
            "filesystem.search", parent="filesystem",
            description="Search files by name or content",
            required_permission="FILESYSTEM_READ",
            scope=CapabilityScope.SAFE, tags=("io", "search"),
        )
        self.register(
            "filesystem.delete", parent="filesystem",
            description="Delete files or directories",
            required_permission="FILESYSTEM_WRITE",
            scope=CapabilityScope.DESTRUCTIVE, tags=("io",),
        )

        # Browser
        self.register("browser", description="Web browser automation")
        self.register(
            "browser.navigate", parent="browser",
            description="Navigate to a URL",
            required_permission="NETWORK_HTTP",
            scope=CapabilityScope.SAFE, tags=("web",),
        )
        self.register(
            "browser.extract", parent="browser",
            description="Extract DOM/text/content from a page",
            required_permission="NETWORK_HTTP",
            scope=CapabilityScope.SAFE, tags=("web",),
        )
        self.register(
            "browser.download", parent="browser",
            description="Download files via the browser",
            required_permission="NETWORK_HTTP",
            scope=CapabilityScope.INTERACTIVE, tags=("web", "io"),
        )

        # Git
        self.register("git", description="Version control with git")
        self.register(
            "git.clone", parent="git",
            description="Clone a repository",
            required_permission="NETWORK_HTTP",
            scope=CapabilityScope.SAFE, tags=("vcs",),
        )
        self.register(
            "git.commit", parent="git",
            description="Create a commit",
            required_permission="FILESYSTEM_WRITE",
            scope=CapabilityScope.INTERACTIVE, tags=("vcs",),
        )
        self.register(
            "git.push", parent="git",
            description="Push commits to a remote",
            required_permission="NETWORK_HTTP",
            scope=CapabilityScope.PRIVILEGED, tags=("vcs",),
        )
        self.register(
            "git.review", parent="git",
            description="Review diffs and pull requests",
            required_permission="FILESYSTEM_READ",
            scope=CapabilityScope.SAFE, tags=("vcs",),
        )

        # Terminal / Process
        self.register("terminal", description="Local shell execution")
        self.register(
            "terminal.exec", parent="terminal",
            description="Execute shell commands",
            required_permission="PROCESS_EXEC",
            scope=CapabilityScope.PRIVILEGED, tags=("exec",),
        )

        # Network
        self.register("network", description="Network access")
        self.register(
            "network.http", parent="network",
            description="Make outbound HTTP requests",
            required_permission="NETWORK_HTTP",
            scope=CapabilityScope.SAFE, tags=("web",),
        )
        self.register(
            "network.websocket", parent="network",
            description="Open websocket connections",
            required_permission="NETWORK_TCP",
            scope=CapabilityScope.INTERACTIVE, tags=("web",),
        )

        # Docker
        self.register("docker", description="Container management")
        self.register(
            "docker.run", parent="docker",
            description="Run a container",
            required_permission="PROCESS_EXEC",
            scope=CapabilityScope.PRIVILEGED, tags=("containers",),
        )
        self.register(
            "docker.build", parent="docker",
            description="Build an image",
            required_permission="PROCESS_EXEC",
            scope=CapabilityScope.PRIVILEGED, tags=("containers",),
        )
        self.register(
            "docker.logs", parent="docker",
            description="Read container logs",
            required_permission="PROCESS_EXEC",
            scope=CapabilityScope.SAFE, tags=("containers",),
        )

        # Database
        self.register("database", description="Database access")
        self.register(
            "database.read", parent="database",
            description="Read from a database",
            required_permission="DATABASE_READ",
            scope=CapabilityScope.SAFE, tags=("data",),
        )
        self.register(
            "database.write", parent="database",
            description="Write to a database",
            required_permission="DATABASE_WRITE",
            scope=CapabilityScope.DESTRUCTIVE, tags=("data",),
        )

        # Desktop
        self.register("desktop", description="Desktop environment access")
        self.register(
            "desktop.clipboard", parent="desktop",
            description="Read/write the system clipboard",
            required_permission="DESKTOP_KEYBOARD",
            scope=CapabilityScope.INTERACTIVE, tags=("ui",),
        )
        self.register(
            "desktop.notify", parent="desktop",
            description="Show system notifications",
            required_permission="DESKTOP_KEYBOARD",
            scope=CapabilityScope.SAFE, tags=("ui",),
        )
        self.register(
            "desktop.screenshot", parent="desktop",
            description="Capture the screen",
            required_permission="SCREEN_CAPTURE",
            scope=CapabilityScope.INTERACTIVE, tags=("ui",),
        )

        # Memory
        self.register("memory", description="Memory subsystem access")
        self.register(
            "memory.store", parent="memory",
            description="Persist facts or episodes",
            required_permission="FILESYSTEM_WRITE",
            scope=CapabilityScope.SAFE, tags=("memory",),
        )
        self.register(
            "memory.retrieve", parent="memory",
            description="Retrieve from memory",
            required_permission="FILESYSTEM_READ",
            scope=CapabilityScope.SAFE, tags=("memory",),
        )


# Module-level child index (shared across instances intentionally:
# the catalog is a singleton source of truth within a process).
_CHILDREN: dict[str, list[str]] = {}


__all__ = [
    "CapabilityCatalog",
    "CapabilityNode",
    "CapabilityScope",
]
