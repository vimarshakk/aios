"""Plugin sandbox — lightweight isolation for plugin execution.

The sandbox provides a restricted execution context for plugins.  In M1
this is a thin wrapper; full OS-level isolation (containers, seccomp)
is planned for M2+.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SandboxConfig:
    """Configuration for plugin sandboxing.

    Attributes:
        allowed_permissions: Permissions the sandboxed plugin may use.
        network_access: Whether the plugin can make network calls.
        filesystem_paths: Paths the plugin may read/write.
        timeout_seconds: Max execution time per call (None = unlimited).
    """

    allowed_permissions: tuple[str, ...] = ()
    network_access: bool = False
    filesystem_paths: tuple[str, ...] = ()
    timeout_seconds: float | None = None


@dataclass
class SandboxResult:
    """Result of a sandboxed execution.

    Attributes:
        output: The return value from the callable.
        blocked: Permissions that were denied during execution.
        timed_out: True if the execution exceeded the timeout.
    """

    output: Any = None
    blocked: list[str] = field(default_factory=list)
    timed_out: bool = False


class PluginSandbox:
    """Execute plugin code within a restricted context.

    For M1, the sandbox is advisory — it records what would be blocked
    but does not enforce OS-level restrictions.
    """

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self.config = config or SandboxConfig()

    def check_permission(self, perm: str) -> bool:
        """Return True if the permission is allowed by the sandbox."""
        if self.config.allowed_permissions:
            return perm in self.config.allowed_permissions
        return True  # no restrictions configured → allow all

    def filter_permissions(self, perms: list[str]) -> tuple[list[str], list[str]]:
        """Split permissions into (allowed, blocked) lists."""
        allowed: list[str] = []
        blocked: list[str] = []
        for p in perms:
            if self.check_permission(p):
                allowed.append(p)
            else:
                blocked.append(p)
        return allowed, blocked


class PermissionPolicy:
    """Marketplace-enforced permission policy for plugins.

    Defines which permissions are safe, which require approval, and
    which are always denied.
    """

    SAFE: frozenset[str] = frozenset({
        "memory.read",
        "memory.write",
        "workflow.read",
        "capability.query",
    })

    REQUIRES_APPROVAL: frozenset[str] = frozenset({
        "network.http",
        "network.https",
        "filesystem.read",
        "capability.register",
    })

    DENIED: frozenset[str] = frozenset({
        "filesystem.write",
        "system.exec",
        "system.shell",
        "admin.all",
    })

    def classify(self, perm: str) -> str:
        """Classify a permission as 'safe', 'approval', or 'denied'."""
        if perm in self.DENIED:
            return "denied"
        if perm in self.REQUIRES_APPROVAL:
            return "approval"
        return "safe"

    def is_allowed(self, perm: str, approved: frozenset[str] | None = None) -> bool:
        """Check if a permission is allowed given the current approval set."""
        classification = self.classify(perm)
        if classification == "denied":
            return False
        if classification == "safe":
            return True
        # Requires approval — check if it's in the approved set
        return approved is not None and perm in approved

    def check_manifest(
        self,
        permissions: tuple[str, ...],
        approved: frozenset[str] | None = None,
    ) -> tuple[list[str], list[str]]:
        """Check a manifest's permissions. Returns (allowed, denied)."""
        allowed: list[str] = []
        denied: list[str] = []
        for p in permissions:
            if self.is_allowed(p, approved):
                allowed.append(p)
            else:
                denied.append(p)
        return allowed, denied
