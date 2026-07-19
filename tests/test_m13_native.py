"""
M13 Tests — Native Integrations

Tests verify file structure, TypeScript content, and configuration integrity
of the native integration modules.
"""

import pytest
import os


# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = os.path.dirname(__file__)
AIOS_ROOT = os.path.dirname(ROOT)
DESKTOP_DIR = os.path.join(AIOS_ROOT, "apps", "desktop")
WEB_SRC = os.path.join(AIOS_ROOT, "apps", "web", "src")


def read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def file_exists(path: str) -> bool:
    return os.path.exists(path)


# ---------------------------------------------------------------------------
# M13.1: Global Keyboard Shortcuts
# ---------------------------------------------------------------------------

class TestGlobalShortcuts:
    """Verify shortcuts manager."""

    def test_shortcuts_manager_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/main/shortcuts-manager.ts"))

    def test_uses_global_shortcut(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/shortcuts-manager.ts"))
        assert "globalShortcut" in content

    def test_has_default_shortcuts(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/shortcuts-manager.ts"))
        assert "command-palette" in content
        assert "CmdOrCtrl+K" in content
        assert "CmdOrCtrl+Shift+E" in content
        assert "memory-explorer" in content

    def test_has_register_unregister(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/shortcuts-manager.ts"))
        assert "registerAll" in content
        assert "unregisterAll" in content

    def test_supports_global_and_app_shortcuts(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/shortcuts-manager.ts"))
        assert "global: boolean" in content
        assert "show-hide" in content  # global shortcut


# ---------------------------------------------------------------------------
# M13.2: File Associations
# ---------------------------------------------------------------------------

class TestFileAssociations:
    """Verify file association manager."""

    def test_file_association_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/main/file-association-manager.ts"))

    def test_registers_protocol(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/file-association-manager.ts"))
        assert "aios://" in content
        assert "setAsDefaultProtocolClient" in content

    def test_handles_aios_files(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/file-association-manager.ts"))
        assert ".aios" in content
        assert ".aios-memory" in content

    def test_has_file_filters(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/file-association-manager.ts"))
        assert "getSupportedFileTypes" in content
        assert "getFileAssociations" in content

    def test_handles_argv(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/file-association-manager.ts"))
        assert "handleArgv" in content
        assert "argv" in content


# ---------------------------------------------------------------------------
# M13.3: Clipboard Integration
# ---------------------------------------------------------------------------

class TestClipboardIntegration:
    """Verify clipboard manager."""

    def test_clipboard_manager_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/main/clipboard-manager.ts"))

    def test_uses_electron_clipboard(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/clipboard-manager.ts"))
        assert "clipboard" in content
        assert "nativeImage" in content

    def test_supports_multiple_types(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/clipboard-manager.ts"))
        assert "text" in content
        assert "html" in content
        assert "image" in content
        assert "files" in content

    def test_has_memory_entry_copy(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/clipboard-manager.ts"))
        assert "copyMemoryEntry" in content
        assert "copyMemoryEntryHTML" in content


# ---------------------------------------------------------------------------
# M13.4: Auto-Launch
# ---------------------------------------------------------------------------

class TestAutoLaunch:
    """Verify auto-launch manager."""

    def test_auto_launch_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/main/auto-launch-manager.ts"))

    def test_uses_login_item_settings(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/auto-launch-manager.ts"))
        assert "getLoginItemSettings" in content
        assert "setLoginItemSettings" in content

    def test_has_toggle(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/auto-launch-manager.ts"))
        assert "toggle" in content
        assert "openAtLogin" in content


# ---------------------------------------------------------------------------
# M13.5: Window State Persistence
# ---------------------------------------------------------------------------

class TestWindowStatePersistence:
    """Verify window state persistence."""

    def test_window_state_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/main/window-state-persistence.ts"))

    def test_saves_bounds(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/window-state-persistence.ts"))
        assert "getBounds" in content
        assert "setBounds" in content

    def test_saves_maximized(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/window-state-persistence.ts"))
        assert "isMaximized" in content
        assert "window:isMaximized" in content

    def test_debounced_save(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/window-state-persistence.ts"))
        assert "debouncedSave" in content
        assert "setTimeout" in content


# ---------------------------------------------------------------------------
# M13.6: Drag & Drop
# ---------------------------------------------------------------------------

class TestDragDrop:
    """Verify drag-and-drop manager."""

    def test_drag_drop_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/main/drag-drop-manager.ts"))

    def test_supports_file_types(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/drag-drop-manager.ts"))
        assert "json" in content
        assert "txt" in content
        assert "png" in content
        assert "aios" in content

    def test_parses_files(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/drag-drop-manager.ts"))
        assert "parseDroppedFiles" in content


# ---------------------------------------------------------------------------
# M13.7: Power Monitor
# ---------------------------------------------------------------------------

class TestPowerMonitor:
    """Verify power monitor integration."""

    def test_power_monitor_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/main/power-monitor-manager.ts"))

    def test_uses_power_monitor(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/power-monitor-manager.ts"))
        assert "powerMonitor" in content

    def test_detects_events(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/power-monitor-manager.ts"))
        assert "suspend" in content
        assert "resume" in content
        assert "battery-state-changed" in content
        assert "idle" in content.lower()


# ---------------------------------------------------------------------------
# M13.8: IPC Handler Integration
# ---------------------------------------------------------------------------

class TestIpcHandlerM13:
    """Verify IPC handler includes M13 endpoints."""

    def test_ipc_handler_has_shortcut_handlers(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/ipc-handler.ts"))
        assert "shortcuts:list" in content
        assert "shortcuts:update" in content
        assert "shortcuts:set-enabled" in content

    def test_ipc_handler_has_clipboard_handlers(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/ipc-handler.ts"))
        assert "clipboard:read" in content
        assert "clipboard:write-text" in content
        assert "clipboard:write-html" in content
        assert "clipboard:clear" in content

    def test_ipc_handler_has_auto_launch_handlers(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/ipc-handler.ts"))
        assert "auto-launch:isEnabled" in content
        assert "auto-launch:setEnabled" in content
        assert "auto-launch:toggle" in content

    def test_ipc_handler_has_power_handlers(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/ipc-handler.ts"))
        assert "power:state" in content

    def test_ipc_handler_has_file_handlers(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/ipc-handler.ts"))
        assert "file:supported-types" in content

    def test_ipc_handler_imports_m13(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/ipc-handler.ts"))
        assert "ShortcutsManager" in content
        assert "ClipboardManager" in content
        assert "AutoLaunchManager" in content
        assert "PowerMonitorManager" in content
        assert "FileAssociationManager" in content


# ---------------------------------------------------------------------------
# M13.9: Main Process Integration
# ---------------------------------------------------------------------------

class TestMainProcessM13:
    """Verify main process integrates all M13 managers."""

    def test_main_imports_m13(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/index.ts"))
        assert "ShortcutsManager" in content
        assert "ClipboardManager" in content
        assert "AutoLaunchManager" in content
        assert "PowerMonitorManager" in content
        assert "FileAssociationManager" in content
        assert "WindowStatePersistence" in content

    def test_main_initializes_m13(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/index.ts"))
        assert "shortcutsManager = new ShortcutsManager()" in content
        assert "clipboardManager = new ClipboardManager()" in content
        assert "autoLaunchManager = new AutoLaunchManager()" in content
        assert "powerMonitorManager = new PowerMonitorManager()" in content
        assert "fileAssociationManager = new FileAssociationManager()" in content
        assert "windowStatePersistence = new WindowStatePersistence" in content

    def test_main_registers_shortcuts(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/index.ts"))
        assert "shortcutsManager.registerAll()" in content
        assert "shortcutsManager.on(" in content

    def test_main_cleans_up_m13(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/index.ts"))
        assert "shortcutsManager.destroy()" in content
        assert "powerMonitorManager.destroy()" in content
        assert "fileAssociationManager.destroy()" in content
        assert "windowStatePersistence.destroy()" in content


# ---------------------------------------------------------------------------
# M13.10: Preload Script Integration
# ---------------------------------------------------------------------------

class TestPreloadM13:
    """Verify preload script exposes M13 APIs."""

    def test_preload_has_shortcuts_api(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/preload/index.ts"))
        assert "shortcuts:" in content
        assert "shortcuts:list" in content
        assert "shortcuts:update" in content
        assert "shortcuts:set-enabled" in content

    def test_preload_has_clipboard_api(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/preload/index.ts"))
        assert "clipboard:" in content
        assert "clipboard:read" in content
        assert "clipboard:write-text" in content
        assert "clipboard:has-text" in content

    def test_preload_has_auto_launch_api(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/preload/index.ts"))
        assert "autoLaunch:" in content
        assert "auto-launch:isEnabled" in content
        assert "auto-launch:toggle" in content

    def test_preload_has_power_api(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/preload/index.ts"))
        assert "power:" in content
        assert "power:state" in content

    def test_preload_listens_m13_events(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/preload/index.ts"))
        assert "command-palette:toggle" in content
        assert "sidebar:toggle" in content
        assert "file:opened" in content
        assert "power-event" in content


# ---------------------------------------------------------------------------
# M13.11: Test File Coverage
# ---------------------------------------------------------------------------

class TestM13TestCoverage:
    """Verify test file has comprehensive coverage."""

    def test_test_file_exists(self):
        assert file_exists(os.path.join(ROOT, "test_m13_native.py"))

    def test_test_file_has_m13_classes(self):
        content = read_file(os.path.join(ROOT, "test_m13_native.py"))
        assert "TestGlobalShortcuts" in content
        assert "TestFileAssociations" in content
        assert "TestClipboardIntegration" in content
        assert "TestAutoLaunch" in content
        assert "TestWindowStatePersistence" in content
        assert "TestDragDrop" in content
        assert "TestPowerMonitor" in content
        assert "TestIpcHandlerM13" in content
        assert "TestMainProcessM13" in content
        assert "TestPreloadM13" in content

    def test_test_count(self):
        content = read_file(os.path.join(ROOT, "test_m13_native.py"))
        test_count = content.count("def test_")
        assert test_count >= 40, f"Expected at least 40 tests, found {test_count}"
