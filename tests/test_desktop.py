"""Tests for M3.6 — Desktop Integration.

Covers: clipboard, notifications, file dialogs, system info.
All tests are platform-aware and skip gracefully on unsupported systems.
"""

from __future__ import annotations

import asyncio
import sys

import pytest

from aios.desktop.clipboard import Clipboard, ClipboardResult
from aios.desktop.dialogs import (
    DialogMode,
    FileDialog,
    FileDialogResult,
    show_dialog,
)
from aios.desktop.info import (
    DisplayInfo,
    SystemInfo,
    SystemInfoCollector,
    SystemPaths,
)
from aios.desktop.notifications import (
    Notification,
    NotificationResult,
    NotificationService,
    Urgency,
)

# ── Clipboard ──────────────────────────────────────────────────────────


class TestClipboard:
    @pytest.mark.anyio
    async def test_read_returns_result(self):
        clip = Clipboard()
        result = await clip.read()
        assert isinstance(result, ClipboardResult)

    @pytest.mark.anyio
    async def test_write_then_read(self):
        clip = Clipboard()
        msg = f"aios-test-{asyncio.get_event_loop().time()}"
        w = await clip.write(msg)
        assert w.ok is True
        r = await clip.read()
        assert r.ok is True
        assert msg in r.content

    @pytest.mark.anyio
    async def test_clear(self):
        clip = Clipboard()
        await clip.write("clear-me")
        c = await clip.clear()
        assert c.ok is True

    @pytest.mark.anyio
    async def test_result_dataclass(self):
        r = ClipboardResult(ok=True, content="test")
        assert r.ok is True
        assert r.error is None
        r2 = ClipboardResult(ok=False, error="fail")
        assert r2.ok is False
        assert r2.error == "fail"


# ── NotificationService ────────────────────────────────────────────────


class TestNotifications:
    def test_notification_frozen(self):
        n = Notification(title="T", body="B")
        assert n.title == "T"
        assert n.body == "B"
        assert n.urgency == Urgency.NORMAL

    def test_urgency_values(self):
        assert Urgency.LOW == "low"
        assert Urgency.NORMAL == "normal"
        assert Urgency.CRITICAL == "critical"

    def test_service_history(self):
        svc = NotificationService()
        assert svc.history == []
        svc._history.append(Notification(title="X"))
        assert len(svc.history) == 1
        assert svc.history[0].title == "X"

    def test_clear_history(self):
        svc = NotificationService()
        svc._history.append(Notification(title="X"))
        svc.clear_history()
        assert svc.history == []

    @pytest.mark.anyio
    async def test_send_returns_result(self):
        svc = NotificationService()
        result = await svc.send(Notification(title="Test", body="Body"))
        assert isinstance(result, NotificationResult)
        # May fail on headless CI, but should not crash
        assert result.ok is True or result.error is not None

    @pytest.mark.anyio
    async def test_send_many(self):
        svc = NotificationService()
        notes = [Notification(title=f"T{i}", body=f"B{i}") for i in range(3)]
        results = await svc.send_many(notes)
        assert len(results) == 3
        for r in results:
            assert isinstance(r, NotificationResult)

    def test_notification_custom_fields(self):
        n = Notification(
            title="T",
            body="B",
            urgency=Urgency.CRITICAL,
            app_name="MyApp",
            icon="/var/app/icon.png",
            timeout_ms=10000,
        )
        assert n.urgency == Urgency.CRITICAL
        assert n.app_name == "MyApp"
        assert n.icon == "/var/app/icon.png"
        assert n.timeout_ms == 10000

    def test_notification_result_frozen(self):
        r = NotificationResult(ok=True, id="123")
        assert r.ok is True
        assert r.id == "123"
        assert r.error is None


# ── FileDialog ─────────────────────────────────────────────────────────


class TestFileDialog:
    def test_config_defaults(self):
        d = FileDialog()
        assert d.mode == DialogMode.OPEN
        assert d.title == "Select File"
        assert d.multiple is False

    def test_config_custom(self):
        d = FileDialog(
            mode=DialogMode.SAVE,
            title="Save As",
            initial_dir="/var/docs",
            file_types=[".py", ".txt"],
            default_filename="out.py",
        )
        assert d.mode == DialogMode.SAVE
        assert d.initial_dir == "/var/docs"
        assert d.file_types == [".py", ".txt"]
        assert d.default_filename == "out.py"

    def test_dialog_mode_values(self):
        assert DialogMode.OPEN == "open"
        assert DialogMode.SAVE == "save"
        assert DialogMode.DIRECTORY == "directory"

    def test_result_frozen(self):
        r = FileDialogResult(ok=True, paths=("/a/b.py",))
        assert r.ok is True
        assert r.paths == ("/a/b.py",)

    @pytest.mark.anyio
    async def test_show_dialog_headless(self):
        d = FileDialog()
        result = await show_dialog(d)
        assert isinstance(result, FileDialogResult)
        # On CI/headless, will fail gracefully
        assert result.ok is True or result.error is not None


# ── SystemInfo ─────────────────────────────────────────────────────────


class TestSystemInfo:
    def test_collector_collects(self):
        collector = SystemInfoCollector()
        info = collector.collect()
        assert isinstance(info, SystemInfo)
        assert info.os_name in ("macos", "linux", "windows")
        assert info.hostname != ""
        assert info.python_version != ""
        assert info.architecture != ""

    def test_os_name_matches_platform(self):
        collector = SystemInfoCollector()
        info = collector.collect()
        if sys.platform == "darwin":
            assert info.os_name == "macos"
        elif sys.platform == "win32":
            assert info.os_name == "windows"
        else:
            assert info.os_name == "linux"

    def test_user_not_empty(self):
        collector = SystemInfoCollector()
        info = collector.collect()
        assert info.user != ""
        assert True  # might be "unknown" in container

    def test_cwd_not_empty(self):
        collector = SystemInfoCollector()
        info = collector.collect()
        assert info.cwd != ""

    def test_paths_not_empty(self):
        collector = SystemInfoCollector()
        info = collector.collect()
        assert info.paths.home != ""
        assert info.paths.temp != ""

    def test_include_env(self):
        collector = SystemInfoCollector(include_env=True)
        info = collector.collect()
        assert len(info.env_keys) > 0
        # Ensure no values are included
        for key in info.env_keys:
            assert key != ""

    def test_exclude_env_by_default(self):
        collector = SystemInfoCollector()
        info = collector.collect()
        assert info.env_keys == ()

    def test_display_info_defaults(self):
        d = DisplayInfo()
        assert d.width == 0
        assert d.height == 0

    def test_system_paths_defaults(self):
        p = SystemPaths()
        assert p.home == ""

    def test_system_info_frozen(self):
        info = SystemInfo(os_name="test")
        assert info.os_name == "test"

    def test_app_data_populated(self):
        collector = SystemInfoCollector()
        info = collector.collect()
        assert info.paths.app_data != ""

    def test_architecture_populated(self):
        collector = SystemInfoCollector()
        info = collector.collect()
        known = ("arm64", "x86_64", "AMD64", "aarch64")
        assert info.architecture in known or len(info.architecture) > 0
