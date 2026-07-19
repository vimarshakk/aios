"""Clipboard access — read and write text to the system clipboard.

Provides an async interface to the OS clipboard. Falls back to a
process-based approach using subprocess for portability.
"""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class ClipboardResult:
    """Result of a clipboard operation.

    Attributes:
        ok: Whether the operation succeeded.
        content: The text content read (for reads) or written (for writes).
        error: Error message if the operation failed.
    """

    ok: bool
    content: str = ""
    error: str | None = None


class Clipboard:
    """Async clipboard access.

    Uses platform-appropriate commands (pbcopy/pbpaste on macOS,
    xclip/xsel on Linux, powershell on Windows).

    Usage::

        clip = Clipboard()
        result = await clip.read()
        await clip.write("Hello, world!")
    """

    def __init__(self) -> None:
        self._platform = _detect_platform()

    async def read(self) -> ClipboardResult:
        """Read text from the system clipboard."""
        cmd = _get_read_command(self._platform)
        if cmd is None:
            return ClipboardResult(ok=False, error=f"Unsupported platform: {self._platform}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err = stderr.decode(errors="replace").strip()
                return ClipboardResult(ok=False, error=err or f"Exit code {proc.returncode}")
            return ClipboardResult(ok=True, content=stdout.decode(errors="replace"))
        except FileNotFoundError as exc:
            return ClipboardResult(ok=False, error=f"Clipboard command not found: {exc}")
        except Exception as exc:
            return ClipboardResult(ok=False, error=str(exc))

    async def write(self, text: str) -> ClipboardResult:
        """Write text to the system clipboard."""
        cmd = _get_write_command(self._platform)
        if cmd is None:
            return ClipboardResult(ok=False, error=f"Unsupported platform: {self._platform}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await proc.communicate(input=text.encode())
            if proc.returncode != 0:
                err = stderr.decode(errors="replace").strip()
                return ClipboardResult(ok=False, error=err or f"Exit code {proc.returncode}")
            return ClipboardResult(ok=True, content=text)
        except FileNotFoundError as exc:
            return ClipboardResult(ok=False, error=f"Clipboard command not found: {exc}")
        except Exception as exc:
            return ClipboardResult(ok=False, error=str(exc))

    async def clear(self) -> ClipboardResult:
        """Clear the system clipboard."""
        return await self.write("")


def _detect_platform() -> str:
    import sys
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    return "linux"


def _get_read_command(platform: str) -> list[str] | None:
    if platform == "macos":
        return ["pbpaste"]
    if platform == "windows":
        return ["powershell", "-command", "Get-Clipboard"]
    if platform == "linux":
        if shutil.which("xclip"):
            return ["xclip", "-selection", "clipboard", "-o"]
        if shutil.which("xsel"):
            return ["xsel", "--clipboard", "--output"]
        if shutil.which("wl-paste"):
            return ["wl-paste"]
    return None


def _get_write_command(platform: str) -> list[str] | None:
    if platform == "macos":
        return ["pbcopy"]
    if platform == "windows":
        return ["powershell", "-command", "Set-Clipboard"]
    if platform == "linux":
        if shutil.which("xclip"):
            return ["xclip", "-selection", "clipboard"]
        if shutil.which("xsel"):
            return ["xsel", "--clipboard", "--input"]
        if shutil.which("wl-copy"):
            return ["wl-copy"]
    return None


__all__ = [
    "Clipboard",
    "ClipboardResult",
]
