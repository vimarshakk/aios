"""System information — OS details, display, paths, and environment.

Provides a read-only view of the system environment for agent awareness.
All data is collected at access time and cached for the session.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class DisplayInfo:
    """Display/monitor information.

    Attributes:
        width: Screen width in pixels.
        height: Screen height in pixels.
        scale_factor: Display scale factor (1.0 = normal).
        name: Display name (if available).
    """

    width: int = 0
    height: int = 0
    scale_factor: float = 1.0
    name: str = ""


@dataclass(frozen=True)
class SystemPaths:
    """Common system directories.

    Attributes:
        home: User home directory.
        desktop: Desktop directory.
        documents: Documents directory.
        downloads: Downloads directory.
        temp: Temporary directory.
        app_data: Application data directory.
    """

    home: str = ""
    desktop: str = ""
    documents: str = ""
    downloads: str = ""
    temp: str = ""
    app_data: str = ""


@dataclass(frozen=True)
class SystemInfo:
    """Complete system information snapshot.

    Attributes:
        os_name: Operating system name (e.g. "macos", "linux", "windows").
        os_version: OS version string.
        os_release: OS release details.
        hostname: Machine hostname.
        python_version: Python version string.
        architecture: Machine architecture (e.g. "arm64", "x86_64").
        user: Current username.
        cwd: Current working directory.
        display: Display information.
        paths: Common system paths.
        env_keys: List of environment variable keys (values redacted).
    """

    os_name: str = ""
    os_version: str = ""
    os_release: str = ""
    hostname: str = ""
    python_version: str = ""
    architecture: str = ""
    user: str = ""
    cwd: str = ""
    display: DisplayInfo = field(default_factory=DisplayInfo)
    paths: SystemPaths = field(default_factory=SystemPaths)
    env_keys: tuple[str, ...] = ()


class SystemInfoCollector:
    """Collects system information.

    Usage::

        collector = SystemInfoCollector()
        info = collector.collect()
        print(info.os_name, info.hostname)
    """

    def __init__(self, *, include_env: bool = False) -> None:
        """Initialize the collector.

        Args:
            include_env: If True, include environment variable keys in the result.
                        Values are never included for security.
        """
        self._include_env = include_env

    def collect(self) -> SystemInfo:
        """Collect current system information."""
        return SystemInfo(
            os_name=self._get_os_name(),
            os_version=platform.version(),
            os_release=platform.release(),
            hostname=platform.node(),
            python_version=platform.python_version(),
            architecture=platform.machine(),
            user=self._get_user(),
            cwd=str(Path.cwd()),
            display=self._get_display(),
            paths=self._get_paths(),
            env_keys=self._get_env_keys() if self._include_env else (),
        )

    def _get_os_name(self) -> str:
        if sys.platform == "darwin":
            return "macos"
        if sys.platform == "win32":
            return "windows"
        if sys.platform.startswith("linux"):
            return "linux"
        return sys.platform

    def _get_user(self) -> str:
        return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))

    def _get_paths(self) -> SystemPaths:
        home = Path.home()
        return SystemPaths(
            home=str(home),
            desktop=str(home / "Desktop"),
            documents=str(home / "Documents"),
            downloads=str(home / "Downloads"),
            temp=os.environ.get("TMPDIR", ""),
            app_data=self._get_app_data(home),
        )

    def _get_app_data(self, home: Path) -> str:
        if sys.platform == "darwin":
            return str(home / "Library" / "Application Support")
        if sys.platform == "win32":
            return os.environ.get("APPDATA", str(home / "AppData" / "Roaming"))
        return os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))

    def _get_display(self) -> DisplayInfo:
        """Try to get display info. Returns empty on headless systems."""
        if sys.platform == "darwin":
            return self._get_macos_display()
        if sys.platform == "linux":
            return self._get_linux_display()
        return DisplayInfo()

    def _get_macos_display(self) -> DisplayInfo:
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],  # noqa: S607
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if "Resolution:" in line:
                    parts = line.split("Resolution:")[1].strip()
                    wh = parts.split("x")
                    if len(wh) == 2:
                        return DisplayInfo(
                            width=int(wh[0].strip()),
                            height=int(wh[1].strip().split()[0]),
                        )
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass
        return DisplayInfo()

    def _get_linux_display(self) -> DisplayInfo:
        try:
            result = subprocess.run(
                ["xrandr", "--query"],  # noqa: S607
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if " connected" in line and " x " in line:
                    parts = line.split(" x ")
                    if len(parts) >= 2:
                        w = parts[0].split()[-1]
                        h = parts[1].split()[0]
                        return DisplayInfo(width=int(w), height=int(h))
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass
        return DisplayInfo()

    def _get_env_keys(self) -> tuple[str, ...]:
        return tuple(sorted(os.environ.keys()))


__all__ = [
    "DisplayInfo",
    "SystemInfo",
    "SystemInfoCollector",
    "SystemPaths",
]
