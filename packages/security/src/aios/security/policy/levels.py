"""Approval levels and sensitivity constants for the policy engine."""

from __future__ import annotations

from enum import StrEnum

from aios.agents.permissions import Permission


class ApprovalLevel(StrEnum):
    """How an action must be approved before execution.

    Attributes:
        ALLOW: No approval needed; auto-granted if permissions suffice.
        ASK_ONCE: Prompt the user once per session for this action.
        ASK_ALWAYS: Prompt before every execution.
        DENY: Action is forbidden regardless of permissions.
    """

    ALLOW = "allow"
    ASK_ONCE = "ask_once"
    ASK_ALWAYS = "ask_always"
    DENY = "deny"


# Permissions that are always treated as sensitive (>= ASK_ONCE).
SENSITIVE_PERMISSIONS: frozenset[str] = frozenset({
    Permission.FILESYSTEM_WRITE,
    Permission.NETWORK_TCP,
    Permission.DESKTOP_MOUSE,
    Permission.DESKTOP_KEYBOARD,
    Permission.PROCESS_EXEC,
    Permission.DATABASE_WRITE,
    Permission.VOICE_RECORD,
    Permission.SCREEN_CAPTURE,
})

# Permissions that policy always forbids (destructive / high-risk).
FORBIDDEN_PERMISSIONS: frozenset[str] = frozenset({
    "system.shutdown",
    "filesystem.format",
})


__all__ = [
    "FORBIDDEN_PERMISSIONS",
    "SENSITIVE_PERMISSIONS",
    "ApprovalLevel",
]
