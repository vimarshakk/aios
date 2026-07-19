"""File dialogs — open/save file dialogs and directory selection.

Provides async wrappers around OS-native file dialogs. Uses subprocess
to invoke platform-appropriate tools. Returns empty results on
unsupported platforms or when the user cancels.
"""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass, field
from enum import StrEnum


class DialogMode(StrEnum):
    """File dialog mode."""

    OPEN = "open"
    SAVE = "save"
    DIRECTORY = "directory"


@dataclass(frozen=True)
class FileDialog:
    """Configuration for a file dialog.

    Attributes:
        mode: Dialog mode (open, save, directory).
        title: Dialog window title.
        initial_dir: Starting directory.
        file_types: Allowed file extensions (e.g. [".py", ".txt"]).
        default_filename: Default filename for save dialogs.
        multiple: Allow multiple file selection (open mode only).
    """

    mode: DialogMode = DialogMode.OPEN
    title: str = "Select File"
    initial_dir: str = ""
    file_types: list[str] = field(default_factory=list)
    default_filename: str = ""
    multiple: bool = False


@dataclass(frozen=True)
class FileDialogResult:
    """Result of a file dialog.

    Attributes:
        ok: Whether the user selected a file (not cancelled).
        paths: Selected file paths.
        error: Error message if the dialog failed.
    """

    ok: bool
    paths: tuple[str, ...] = ()
    error: str | None = None


async def show_dialog(config: FileDialog) -> FileDialogResult:
    """Show a file dialog and return the user's selection.

    Args:
        config: Dialog configuration.

    Returns:
        FileDialogResult with selected paths.
    """
    import sys

    if sys.platform == "darwin":
        platform = "macos"
    elif sys.platform == "win32":
        platform = "windows"
    else:
        platform = "linux"
    cmd = _build_dialog_command(platform, config)
    if cmd is None:
        return FileDialogResult(ok=False, error=f"Unsupported platform: {platform}")
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await proc.communicate()
        if proc.returncode != 0:
            output = stdout.decode(errors="replace").strip()
            if not output:
                return FileDialogResult(ok=False, error="User cancelled or dialog failed")
            return FileDialogResult(ok=False, error=output)
        output = stdout.decode(errors="replace").strip()
        if not output:
            return FileDialogResult(ok=False, error="User cancelled")
        paths = tuple(p for p in output.splitlines() if p.strip())
        return FileDialogResult(ok=True, paths=paths)
    except FileNotFoundError as exc:
        return FileDialogResult(ok=False, error=f"Dialog command not found: {exc}")
    except Exception as exc:
        return FileDialogResult(ok=False, error=str(exc))


def _build_dialog_command(platform: str, config: FileDialog) -> list[str] | None:
    if platform == "macos":
        return _build_macos_command(config)
    if platform == "linux":
        return _build_linux_command(config)
    if platform == "windows":
        return _build_windows_command(config)
    return None


def _build_macos_command(config: FileDialog) -> list[str]:
    if config.mode == DialogMode.SAVE:
        script = (
            f'set filePath to POSIX path of (choose file name'
            f' with prompt "{config.title}"'
        )
        if config.initial_dir:
            script += f' default location "{config.initial_dir}"'
        if config.default_filename:
            script += f' default name "{config.default_filename}"'
        script += ")"
    elif config.mode == DialogMode.DIRECTORY:
        script = (
            f'set filePath to POSIX path of (choose folder'
            f' with prompt "{config.title}"'
        )
        if config.initial_dir:
            script += f' default location "{config.initial_dir}"'
        script += ")"
    else:
        if config.multiple:
            script = (
                f'set fileList to (choose file with prompt "{config.title}"'
                f' with multiple selections allowed'
            )
        else:
            script = (
                f'set filePath to POSIX path of (choose file'
                f' with prompt "{config.title}"'
            )
        if config.initial_dir:
            script += f' default location "{config.initial_dir}"'
        if config.file_types:
            types_str = ", ".join(f'"{ft}"' for ft in config.file_types)
            script += f' of type {{{types_str}}}'
        script += ")"
    return ["osascript", "-e", script, "-e", "return filePath"]


def _build_linux_command(config: FileDialog) -> list[str] | None:
    if not shutil.which("zenity"):
        return None
    cmd = ["zenity", "--file-selection"]
    if config.mode == DialogMode.SAVE:
        cmd.append("--save")
        if config.default_filename:
            cmd.extend(["--filename", config.default_filename])
    elif config.mode == DialogMode.DIRECTORY:
        cmd.append("--directory")
    if config.title:
        cmd.extend(["--title", config.title])
    if config.initial_dir:
        cmd.extend(["--filename", config.initial_dir])
    if config.multiple and config.mode == DialogMode.OPEN:
        cmd.append("--multiple")
    if config.file_types:
        filters = " ".join(f'*{ft}' for ft in config.file_types)
        cmd.extend(["--file-filter", f"Files ({filters})"])
    return cmd


def _build_windows_command(config: FileDialog) -> list[str] | None:
    ps_parts = ["Add-Type -AssemblyName System.Windows.Forms"]
    if config.mode == DialogMode.SAVE:
        ps_parts.append("$d = New-Object System.Windows.Forms.SaveFileDialog")
        if config.default_filename:
            ps_parts.append(f"$d.FileName = '{config.default_filename}'")
    elif config.mode == DialogMode.DIRECTORY:
        ps_parts.append("$d = New-Object System.Windows.Forms.FolderBrowserDialog")
    else:
        ps_parts.append("$d = New-Object System.Windows.Forms.OpenFileDialog")
        if config.multiple:
            ps_parts.append("$d.Multiselect = $true")
    if config.title:
        ps_parts.append(f"$d.Title = '{config.title}'")
    if config.initial_dir:
        ps_parts.append(f"$d.InitialDirectory = '{config.initial_dir}'")
    if config.file_types and config.mode != DialogMode.DIRECTORY:
        filter_str = "|".join(f"{ft} files (*{ft})|*{ft}" for ft in config.file_types)
        ps_parts.append(f"$d.Filter = '{filter_str}'")
    ps_parts.append("if ($d.ShowDialog() -eq 'OK') { $d.FileName }")
    script = "; ".join(ps_parts)
    return ["powershell", "-command", script]


__all__ = [
    "DialogMode",
    "FileDialog",
    "FileDialogResult",
    "show_dialog",
]
