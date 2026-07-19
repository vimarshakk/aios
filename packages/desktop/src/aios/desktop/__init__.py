"""AIOS Desktop Integration.

OS-level automation: clipboard, notifications, screen capture, file dialogs, system info.
"""

from __future__ import annotations

from aios.desktop.clipboard import Clipboard
from aios.desktop.dialogs import FileDialog, FileDialogResult
from aios.desktop.info import SystemInfo
from aios.desktop.notifications import Notification, NotificationResult, NotificationService

API_VERSION = "1.0"

__all__ = [
    "API_VERSION",
    "Clipboard",
    "FileDialog",
    "FileDialogResult",
    "Notification",
    "NotificationResult",
    "NotificationService",
    "SystemInfo",
]
