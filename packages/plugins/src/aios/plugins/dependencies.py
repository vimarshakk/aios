"""Dependency graph and resolver for plugin marketplace dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from aios.plugins.versions import SemVer, VersionRange

if TYPE_CHECKING:
    from aios.plugins.marketplace import PluginMarketplace


class DependencyError(Exception):
    """Raised when dependency resolution fails."""


class CircularDependencyError(DependencyError):
    """Raised when a circular dependency is detected."""


class MissingDependencyError(DependencyError):
    """Raised when a required dependency is not found."""


@dataclass(frozen=True, slots=True)
class ResolvedDependency:
    """A resolved dependency with version info.

    Attributes:
        name: Plugin name.
        required_range: The version range expression required by the parent.
        resolved_version: The actual version that satisfies the constraint.
    """

    name: str
    required_range: str
    resolved_version: str


class DependencyResolver:
    """Resolve plugin dependency graphs using topological sort.

    Uses a marketplace to look up available versions and validates that all
    dependency constraints can be satisfied.
    """

    def __init__(self, marketplace: PluginMarketplace) -> None:
        self._marketplace = marketplace

    def get_dependencies(self, name: str) -> dict[str, str]:
        """Return the dependency map for a plugin {name: version_range}."""
        entry = self._marketplace.get(name)
        return dict(entry.dependencies)

    def validate(self, name: str) -> list[ResolvedDependency]:
        """Validate that all dependencies of a plugin can be resolved.

        Returns a flat list of resolved dependencies in install order.
        Raises DependencyError on failure.
        """
        resolved: dict[str, str] = {}  # name → resolved version
        visiting: set[str] = set()
        order: list[str] = []
        errors: list[str] = []

        def visit(plugin_name: str, chain: list[str]) -> None:
            if plugin_name in resolved:
                return
            if plugin_name in visiting:
                cycle = " → ".join([*chain, plugin_name])
                raise CircularDependencyError(
                    f"Circular dependency detected: {cycle}"
                )

            visiting.add(plugin_name)

            try:
                entry = self._marketplace.get(plugin_name)
            except Exception:
                raise MissingDependencyError(
                    f"Dependency '{plugin_name}' not found in marketplace"
                ) from None

            for _dep_name in entry.dependencies:
                visit(_dep_name, [*chain, plugin_name])

            # Resolve version
            entry = self._marketplace.get(plugin_name)
            ver = SemVer.parse(entry.version)
            if entry.dependencies:
                # Check version of this plugin satisfies any constraint
                for _dep_name, dep_range in entry.dependencies.items():
                    vr = VersionRange(dep_range)
                    if not vr.matches(ver):
                        errors.append(
                            f"{plugin_name}@{entry.version} doesn't satisfy "
                            f"constraint {dep_range}"
                        )

            resolved[plugin_name] = entry.version
            order.append(plugin_name)
            visiting.discard(plugin_name)

        visit(name, [])

        if errors:
            raise DependencyError("; ".join(errors))

        return [
            ResolvedDependency(
                name=n,
                required_range="",
                resolved_version=resolved[n],
            )
            for n in order
        ]

    def topological_sort(self, names: list[str]) -> list[str]:
        """Return names in dependency-safe install order.

        Raises CircularDependencyError or MissingDependencyError on failure.
        """
        resolved: set[str] = set()
        visiting: set[str] = set()
        order: list[str] = []

        def visit(name: str) -> None:
            if name in resolved:
                return
            if name in visiting:
                raise CircularDependencyError(
                    f"Circular dependency detected at '{name}'"
                )
            visiting.add(name)

            try:
                entry = self._marketplace.get(name)
            except Exception:
                raise MissingDependencyError(
                    f"Dependency '{name}' not found in marketplace"
                ) from None

            for dep_name in entry.dependencies:
                visit(dep_name)

            resolved.add(name)
            order.append(name)
            visiting.discard(name)

        for name in names:
            visit(name)

        return order
