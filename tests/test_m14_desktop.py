"""
M14 Tests — Desktop Developer Experience

Tests for:
- M14.1: DeveloperConsole
- M14.2: PluginManager
- M14.3: AdvancedWindowManager
- M14.4: SystemIntegration
- M14.5: IPC handler, main process, preload integration
"""

import os
import sys

import pytest

# ── Path setup ──────────────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DESKTOP_DIR = os.path.join(ROOT, "apps", "desktop")
MAIN_DIR = os.path.join(DESKTOP_DIR, "src", "main")
PRELOAD_DIR = os.path.join(DESKTOP_DIR, "src", "preload")


def read_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── M14.1: DeveloperConsole ────────────────────────────────────────────────

class TestDeveloperConsole:
    """Tests for DeveloperConsole module."""

    def test_file_exists(self):
        path = os.path.join(MAIN_DIR, "developer-console.ts")
        assert os.path.exists(path), f"Missing {path}"

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "developer-console.ts"))
        assert "class DeveloperConsole" in content

    def test_has_console_entry_interface(self):
        content = read_file(os.path.join(MAIN_DIR, "developer-console.ts"))
        assert "ConsoleEntry" in content

    def test_has_app_diagnostics(self):
        content = read_file(os.path.join(MAIN_DIR, "developer-console.ts"))
        assert "AppDiagnostics" in content
        assert "getDiagnostics" in content

    def test_has_performance_metrics(self):
        content = read_file(os.path.join(MAIN_DIR, "developer-console.ts"))
        assert "PerformanceMetrics" in content
        assert "getPerformanceMetrics" in content

    def test_has_devtools_toggle(self):
        content = read_file(os.path.join(MAIN_DIR, "developer-console.ts"))
        assert "toggleDevTools" in content
        assert "openDevTools" in content
        assert "closeDevTools" in content

    def test_has_log_capture(self):
        content = read_file(os.path.join(MAIN_DIR, "developer-console.ts"))
        assert "startCapture" in content
        assert "stopCapture" in content

    def test_has_get_logs(self):
        content = read_file(os.path.join(MAIN_DIR, "developer-console.ts"))
        assert "getLogs" in content
        assert "clearLogs" in content

    def test_has_register_ipc(self):
        content = read_file(os.path.join(MAIN_DIR, "developer-console.ts"))
        assert "registerIpcHandlers" in content

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "developer-console.ts"))
        assert "destroy" in content


# ── M14.2: PluginManager ──────────────────────────────────────────────────

class TestPluginManager:
    """Tests for PluginManager module."""

    def test_file_exists(self):
        path = os.path.join(MAIN_DIR, "plugin-manager.ts")
        assert os.path.exists(path), f"Missing {path}"

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "plugin-manager.ts"))
        assert "class PluginManager" in content

    def test_has_plugin_manifest(self):
        content = read_file(os.path.join(MAIN_DIR, "plugin-manager.ts"))
        assert "PluginManifest" in content

    def test_has_plugin_instance(self):
        content = read_file(os.path.join(MAIN_DIR, "plugin-manager.ts"))
        assert "PluginInstance" in content

    def test_has_plugin_api(self):
        content = read_file(os.path.join(MAIN_DIR, "plugin-manager.ts"))
        assert "PluginAPI" in content

    def test_has_scan_plugins(self):
        content = read_file(os.path.join(MAIN_DIR, "plugin-manager.ts"))
        assert "scanPlugins" in content

    def test_has_load_plugin(self):
        content = read_file(os.path.join(MAIN_DIR, "plugin-manager.ts"))
        assert "loadPlugin" in content

    def test_has_activate_deactivate(self):
        content = read_file(os.path.join(MAIN_DIR, "plugin-manager.ts"))
        assert "activatePlugin" in content
        assert "deactivatePlugin" in content

    def test_has_enable_disable(self):
        content = read_file(os.path.join(MAIN_DIR, "plugin-manager.ts"))
        assert "enablePlugin" in content
        assert "disablePlugin" in content

    def test_has_get_plugins(self):
        content = read_file(os.path.join(MAIN_DIR, "plugin-manager.ts"))
        assert "getPlugins" in content

    def test_has_event_emitter(self):
        content = read_file(os.path.join(MAIN_DIR, "plugin-manager.ts"))
        assert "EventEmitter" in content
        assert 'emit("plugin-loaded"' in content

    def test_has_sandboxed_api(self):
        content = read_file(os.path.join(MAIN_DIR, "plugin-manager.ts"))
        assert "createPluginAPI" in content

    def test_has_plugin_state(self):
        content = read_file(os.path.join(MAIN_DIR, "plugin-manager.ts"))
        assert "PluginState" in content

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "plugin-manager.ts"))
        assert "destroy" in content


# ── M14.3: AdvancedWindowManager ──────────────────────────────────────────

class TestAdvancedWindowManager:
    """Tests for AdvancedWindowManager module."""

    def test_file_exists(self):
        path = os.path.join(MAIN_DIR, "advanced-window-manager.ts")
        assert os.path.exists(path), f"Missing {path}"

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "advanced-window-manager.ts"))
        assert "class AdvancedWindowManager" in content

    def test_has_window_config(self):
        content = read_file(os.path.join(MAIN_DIR, "advanced-window-manager.ts"))
        assert "WindowConfig" in content

    def test_has_split_layout(self):
        content = read_file(os.path.join(MAIN_DIR, "advanced-window-manager.ts"))
        assert "SplitLayout" in content
        assert "createSplitView" in content

    def test_has_window_state(self):
        content = read_file(os.path.join(MAIN_DIR, "advanced-window-manager.ts"))
        assert "WindowState" in content
        assert "getWindowState" in content

    def test_has_create_window(self):
        content = read_file(os.path.join(MAIN_DIR, "advanced-window-manager.ts"))
        assert "createWindow" in content

    def test_has_tile_windows(self):
        content = read_file(os.path.join(MAIN_DIR, "advanced-window-manager.ts"))
        assert "tileWindows" in content

    def test_has_cascade_windows(self):
        content = read_file(os.path.join(MAIN_DIR, "advanced-window-manager.ts"))
        assert "cascadeWindows" in content

    def test_has_group_management(self):
        content = read_file(os.path.join(MAIN_DIR, "advanced-window-manager.ts"))
        assert "addToGroup" in content
        assert "removeFromGroup" in content
        assert "getGroup" in content
        assert "closeGroup" in content

    def test_has_window_operations(self):
        content = read_file(os.path.join(MAIN_DIR, "advanced-window-manager.ts"))
        assert "closeWindow" in content
        assert "focusWindow" in content
        assert "minimizeWindow" in content
        assert "maximizeWindow" in content

    def test_has_get_all_windows(self):
        content = read_file(os.path.join(MAIN_DIR, "advanced-window-manager.ts"))
        assert "getAllWindows" in content
        assert "getAllWindowStates" in content

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "advanced-window-manager.ts"))
        assert "destroy" in content


# ── M14.4: SystemIntegration ──────────────────────────────────────────────

class TestSystemIntegration:
    """Tests for SystemIntegration module."""

    def test_file_exists(self):
        path = os.path.join(MAIN_DIR, "system-integration.ts")
        assert os.path.exists(path), f"Missing {path}"

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "system-integration.ts"))
        assert "class SystemIntegration" in content

    def test_has_badge_methods(self):
        content = read_file(os.path.join(MAIN_DIR, "system-integration.ts"))
        assert "setBadgeCount" in content
        assert "setBadgeText" in content
        assert "setBadgeColor" in content
        assert "clearBadge" in content
        assert "updateBadge" in content

    def test_has_progress_methods(self):
        content = read_file(os.path.join(MAIN_DIR, "system-integration.ts"))
        assert "setProgress" in content
        assert "clearProgress" in content

    def test_has_overlay_methods(self):
        content = read_file(os.path.join(MAIN_DIR, "system-integration.ts"))
        assert "setOverlayIcon" in content
        assert "clearOverlayIcon" in content

    def test_has_flash_frame(self):
        content = read_file(os.path.join(MAIN_DIR, "system-integration.ts"))
        assert "flashFrame" in content

    def test_has_tray_management(self):
        content = read_file(os.path.join(MAIN_DIR, "system-integration.ts"))
        assert "createTray" in content
        assert "setToolTip" in content
        assert "setContextMenu" in content

    def test_has_badge_options(self):
        content = read_file(os.path.join(MAIN_DIR, "system-integration.ts"))
        assert "BadgeOptions" in content
        assert "ProgressOptions" in content

    def test_has_get_state_methods(self):
        content = read_file(os.path.join(MAIN_DIR, "system-integration.ts"))
        assert "getBadgeState" in content
        assert "getProgressState" in content

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "system-integration.ts"))
        assert "destroy" in content


# ── M14.5: IPC Handler Integration ────────────────────────────────────────

class TestIpcHandlerM14:
    """Tests for IPC handler M14 integration."""

    def test_ipc_handler_has_devconsole_handlers(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert 'devconsole:logs' in content
        assert 'devconsole:diagnostics' in content
        assert 'devconsole:performance' in content
        assert 'devconsole:toggle-devtools' in content

    def test_ipc_handler_has_plugin_handlers(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert 'plugins:list' in content
        assert 'plugins:scan' in content
        assert 'plugins:load' in content
        assert 'plugins:activate' in content
        assert 'plugins:deactivate' in content

    def test_ipc_handler_has_window_handlers(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert 'windows:create' in content
        assert 'windows:close' in content
        assert 'windows:tile' in content
        assert 'windows:cascade' in content

    def test_ipc_handler_has_system_handlers(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert 'system:set-badge' in content
        assert 'system:clear-badge' in content
        assert 'system:set-progress' in content
        assert 'system:clear-progress' in content

    def test_ipc_handler_imports_m14(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert "DeveloperConsole" in content
        assert "PluginManager" in content
        assert "AdvancedWindowManager" in content
        assert "SystemIntegration" in content

    def test_ipc_handler_has_m14_deps(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert "developerConsole" in content
        assert "pluginManager" in content
        assert "advancedWindowManager" in content
        assert "systemIntegration" in content

    def test_ipc_handler_version_log(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert "M14" in content


# ── M14.5: Main Process Integration ───────────────────────────────────────

class TestMainProcessM14:
    """Tests for main process M14 integration."""

    def test_main_imports_m14(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "DeveloperConsole" in content
        assert "PluginManager" in content
        assert "AdvancedWindowManager" in content
        assert "SystemIntegration" in content

    def test_main_initializes_m14(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "new DeveloperConsole()" in content
        assert "new PluginManager()" in content
        assert "new AdvancedWindowManager(" in content
        assert "new SystemIntegration()" in content

    def test_main_registers_m14_deps(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "developerConsole," in content
        assert "pluginManager," in content
        assert "advancedWindowManager," in content
        assert "systemIntegration," in content

    def test_main_cleans_up_m14(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "developerConsole.destroy()" in content
        assert "pluginManager.destroy()" in content
        assert "advancedWindowManager.destroy()" in content
        assert "systemIntegration.destroy()" in content

    def test_main_activates_plugins(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "scanPlugins" in content
        assert "loadPlugin" in content
        assert "activatePlugin" in content

    def test_main_version_log(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "M13 + M14" in content


# ── M14.5: Preload Integration ────────────────────────────────────────────

class TestPreloadM14:
    """Tests for preload M14 API exposure."""

    def test_preload_has_devconsole_api(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "devconsole:" in content
        assert "devconsole:logs" in content
        assert "devconsole:diagnostics" in content
        assert "devconsole:performance" in content

    def test_preload_has_plugin_api(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "plugins:list" in content
        assert "plugins:load" in content
        assert "plugins:activate" in content

    def test_preload_has_window_api(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "windows:create" in content
        assert "windows:close" in content
        assert "windows:tile" in content
        assert "windows:cascade" in content

    def test_preload_has_system_badge_api(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "system:set-badge" in content
        assert "system:clear-badge" in content

    def test_preload_has_system_progress_api(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "system:set-progress" in content
        assert "system:clear-progress" in content

    def test_preload_listens_m14_events(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "plugin-loaded" in content
        assert "plugin-activated" in content

    def test_preload_api_interfaces(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "devconsole:" in content
        assert "plugins:" in content
        assert "windows:" in content
        assert "systemBadge:" in content
        assert "systemProgress:" in content


# ── M14.5: Test Coverage ──────────────────────────────────────────────────

class TestM14TestCoverage:
    """Meta-tests for M14 test coverage."""

    def test_all_m14_files_exist(self):
        files = [
            "developer-console.ts",
            "plugin-manager.ts",
            "advanced-window-manager.ts",
            "system-integration.ts",
        ]
        for f in files:
            path = os.path.join(MAIN_DIR, f)
            assert os.path.exists(path), f"Missing {path}"

    def test_test_file_exists(self):
        path = os.path.join(ROOT, "tests", "test_m14_desktop.py")
        assert os.path.exists(path), f"Missing {path}"

    def test_test_count(self):
        """Verify minimum test count for M14."""
        path = os.path.join(ROOT, "tests", "test_m14_desktop.py")
        content = read_file(path)
        test_count = content.count("def test_")
        assert test_count >= 45, f"Expected at least 45 tests, found {test_count}"
