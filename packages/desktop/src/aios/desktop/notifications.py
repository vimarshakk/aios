"""System notifications — send OS-level notifications.

Provides cross-platform notification sending with title, body, and
optional urgency level. Falls back to a no-op logger on unsupported
platforms.
"""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from enum import StrEnum


class Urgency(StrEnum):
    """Notification urgency level."""

    LOW = "low"
    NORMAL = "normal"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Notification:
    """A notification to send.

    Attributes:
        title: Notification title.
        body: Notification body text.
        urgency: Urgency level.
        app_name: Application name to display.
        icon: Path to icon file.
        timeout_ms: Timeout in milliseconds (0 = system default).
    """

    title: str
    body: str = ""
    urgency: Urgency = Urgency.NORMAL
    app_name: str = "AIOS"
    icon: str = ""
    timeout_ms: int = 5000


@dataclass(frozen=True)
class NotificationResult:
    """Result of sending a notification.

    Attributes:
        ok: Whether the notification was sent successfully.
        id: Platform notification ID (if available).
        error: Error message if sending failed.
    """

    ok: bool
    id: str = ""
    error: str | None = None


class NotificationService:
    """Cross-platform notification service.

    Supports macOS (osascript), Linux (notify-send), and Windows (powershell).

    Usage::

        svc = NotificationService()
        result = await svc.send(Notification(title="Hello", body="World"))
    """

    def __init__(self) -> None:
        self._platform = _detect_platform()
        self._history: list[Notification] = []

    @property
    def history(self) -> list[Notification]:
        """Return a copy of sent notifications."""
        return list(self._history)

    async def send(self, notification: Notification) -> NotificationResult:
        """Send a system notification.

        Args:
            notification: The notification to send.

        Returns:
            NotificationResult with success status and any error.
        """
        self._history.append(notification)
        cmd = _build_command(self._platform, notification)
        if cmd is None:
            return NotificationResult(
                ok=False, error=f"Unsupported platform: {self._platform}"
            )
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err = stderr.decode(errors="replace").strip()
                return NotificationResult(ok=False, error=err or f"Exit code {proc.returncode}")
            return NotificationResult(ok=True, id=f"notif-{len(self._history)}")
        except FileNotFoundError as exc:
            return NotificationResult(ok=False, error=f"Notification command not found: {exc}")
        except Exception as exc:
            return NotificationResult(ok=False, error=str(exc))

    async def send_many(
        self, notifications: list[Notification]
    ) -> list[NotificationResult]:
        """Send multiple notifications concurrently.

        Args:
            notifications: List of notifications to send.

        Returns:
            List of results, one per notification.
        """
        tasks = [self.send(n) for n in notifications]
        return list(await asyncio.gather(*tasks))

    def clear_history(self) -> None:
        """Clear the notification history."""
        self._history.clear()


def _detect_platform() -> str:
    import sys
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    return "linux"


def _build_command(platform: str, n: Notification) -> list[str] | None:
    if platform == "macos":
        script = f'display notification "{n.body}" with title "{n.title}"'
        if n.app_name:
            script += f' subtitle "{n.app_name}"'
        return ["osascript", "-e", script]
    if platform == "linux":
        if not shutil.which("notify-send"):
            return None
        cmd = ["notify-send"]
        if n.urgency == Urgency.LOW:
            cmd.extend(["-u", "low"])
        elif n.urgency == Urgency.CRITICAL:
            cmd.extend(["-u", "critical"])
        if n.app_name:
            cmd.extend(["-a", n.app_name])
        if n.icon:
            cmd.extend(["-i", n.icon])
        if n.timeout_ms > 0:
            cmd.extend(["-t", str(n.timeout_ms)])
        cmd.extend([n.title, n.body])
        return cmd
    if platform == "windows":
        ps_body = n.body.replace("'", "''")
        ps_title = n.title.replace("'", "''")
        load_asm = "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms')"
        show_box = f"[System.Windows.Forms.MessageBox]::Show('{ps_body}', '{ps_title}')"
        script = f"{load_asm}; {show_box}"
        return ["powershell", "-command", script]
    return None


__all__ = [
    "Notification",
    "NotificationResult",
    "NotificationService",
    "Urgency",
]
