"""Permission model — every tool declares what it needs, runtime enforces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

# ---------------------------------------------------------------------------
# Permission constants
# ---------------------------------------------------------------------------


class Permission:
    """Well-known permission strings.

    Convention: ``<domain>.<action>``.  Custom permissions follow the same
    pattern but use a project-specific domain prefix.
    """

    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    NETWORK_HTTP = "network.http"
    NETWORK_TCP = "network.tcp"
    DESKTOP_MOUSE = "desktop.mouse"
    DESKTOP_KEYBOARD = "desktop.keyboard"
    PROCESS_EXEC = "process.exec"
    DATABASE_READ = "database.read"
    DATABASE_WRITE = "database.write"
    VOICE_RECORD = "voice.record"
    SCREEN_CAPTURE = "screen.capture"


# ---------------------------------------------------------------------------
# PermissionSet — a typed bag of granted permissions
# ---------------------------------------------------------------------------


class PermissionSet:
    """A set of granted permission strings with fast membership testing.

    Supports ``in`` checks and intersection helpers.
    """

    __slots__ = ("_granted",)

    def __init__(self, granted: Sequence[str] = ()) -> None:
        self._granted = frozenset(granted)

    # -- query -------------------------------------------------------------

    def has(self, perm: str) -> bool:
        """Return True if *perm* is granted."""
        return perm in self._granted

    def has_all(self, perms: Sequence[str]) -> bool:
        """Return True if every permission in *perms* is granted."""
        return self._granted.issuperset(perms)

    def missing(self, perms: Sequence[str]) -> list[str]:
        """Return permissions from *perms* that are NOT granted."""
        return [p for p in perms if p not in self._granted]

    def granted(self) -> frozenset[str]:
        """Return the full set of granted permissions."""
        return self._granted

    def __contains__(self, perm: str) -> bool:
        return perm in self._granted

    def __repr__(self) -> str:
        return f"PermissionSet({sorted(self._granted)})"

    def __len__(self) -> int:
        return len(self._granted)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PermissionSet):
            return self._granted == other._granted
        return NotImplemented


# ---------------------------------------------------------------------------
# PermissionRequest / PermissionResult — for interactive approval flows
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PermissionRequest:
    """A request to grant one or more permissions.

    Attributes:
        permissions: Permission strings being requested.
        reason: Human-readable justification.
        source: Identifier of the tool/agent making the request.
    """

    permissions: tuple[str, ...]
    reason: str = ""
    source: str = ""


@dataclass(frozen=True, slots=True)
class PermissionResult:
    """Outcome of evaluating a permission request.

    Attributes:
        granted: Permissions that were approved.
        denied: Permissions that were denied.
        approved: True if ALL requested permissions were granted.
    """

    granted: tuple[str, ...]
    denied: tuple[str, ...]

    @property
    def approved(self) -> bool:
        return len(self.denied) == 0


# ---------------------------------------------------------------------------
# PermissionChecker — the enforcement engine
# ---------------------------------------------------------------------------


@dataclass
class PermissionChecker:
    """Enforce permissions before tool execution.

    Attributes:
        granted: The set of permissions currently granted.
        on_request: Optional callback invoked when a permission check fails
            and interactive approval is desired.  Receives a
            ``PermissionRequest`` and returns a ``PermissionResult``.
    """

    granted: PermissionSet = field(default_factory=PermissionSet)
    on_request: Callable[[PermissionRequest], PermissionResult] | None = None

    # -- core checks -------------------------------------------------------

    def check(self, required: Sequence[str]) -> bool:
        """Return True if every permission in *required* is already granted."""
        return self.granted.has_all(required)

    def check_tool(self, tool: object) -> bool:
        """Return True if *tool*'s ``permissions`` attribute is fully satisfied.

        The *tool* must have a ``permissions`` attribute that is a sequence
        of permission strings (typically ``BaseTool.permissions``).
        """
        required = getattr(tool, "permissions", ())
        return self.granted.has_all(required)

    def enforce(self, required: Sequence[str]) -> PermissionResult:
        """Evaluate *required* permissions against the granted set.

        If there are missing permissions and an ``on_request`` callback is
        set, the callback is invoked to attempt interactive approval.
        """
        missing = self.granted.missing(required)
        if not missing:
            return PermissionResult(granted=tuple(required), denied=())

        if self.on_request is not None:
            req = PermissionRequest(permissions=tuple(missing))
            result = self.on_request(req)
            # Merge newly granted permissions into the active set
            if result.granted:
                new_perms = list(self.granted.granted()) + list(result.granted)
                self.granted = PermissionSet(new_perms)
            # Recalculate after interactive approval
            still_missing = [p for p in missing if p not in result.granted]
            granted = [p for p in required if p in self.granted]
            return PermissionResult(
                granted=tuple(granted),
                denied=tuple(still_missing),
            )

        return PermissionResult(
            granted=tuple(p for p in required if p in self.granted),
            denied=tuple(missing),
        )

    def enforce_tool(self, tool: object) -> PermissionResult:
        """Like ``enforce`` but reads permissions from the tool object."""
        required = getattr(tool, "permissions", ())
        return self.enforce(required)

    # -- mutation ----------------------------------------------------------

    def grant(self, *perms: str) -> None:
        """Add permissions to the granted set."""
        self.granted = PermissionSet(list(self.granted.granted()) + list(perms))

    def revoke(self, *perms: str) -> None:
        """Remove permissions from the granted set."""
        self.granted = PermissionSet(
            p for p in self.granted.granted() if p not in perms
        )


__all__ = [
    "Permission",
    "PermissionChecker",
    "PermissionRequest",
    "PermissionResult",
    "PermissionSet",
]
