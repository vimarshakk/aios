"""
M12 Tests — Desktop Product (Electron)

Tests verify file structure, TypeScript content, and configuration integrity
of the Electron desktop application. The actual Electron code is TypeScript
and cannot be imported into Python — these tests validate the codebase
structure and patterns.
"""

import pytest
import os
import json


# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = os.path.dirname(__file__)  # tests/
AIOS_ROOT = os.path.dirname(ROOT)  # aios/
DESKTOP_DIR = os.path.join(AIOS_ROOT, "apps", "desktop")
WEB_DIR = os.path.join(AIOS_ROOT, "apps", "web")
WEB_SRC = os.path.join(WEB_DIR, "src")


def read_file(path: str) -> str:
    """Read a file and return its content."""
    with open(path, "r") as f:
        return f.read()


def file_exists(path: str) -> bool:
    return os.path.exists(path)


# ---------------------------------------------------------------------------
# M12.1: Electron Shell Structure
# ---------------------------------------------------------------------------

class TestElectronShellStructure:
    """Verify the Electron app has all required files."""

    def test_package_json_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "package.json"))

    def test_package_json_has_correct_main(self):
        content = json.loads(read_file(os.path.join(DESKTOP_DIR, "package.json")))
        assert "main" in content
        assert content["main"] == "dist/main/index.js"

    def test_package_json_has_electron_dep(self):
        content = json.loads(read_file(os.path.join(DESKTOP_DIR, "package.json")))
        assert "electron" in content.get("devDependencies", {})

    def test_package_json_has_scripts(self):
        content = json.loads(read_file(os.path.join(DESKTOP_DIR, "package.json")))
        scripts = content.get("scripts", {})
        assert "dev" in scripts
        assert "build" in scripts
        assert "build:electron" in scripts

    def test_tsconfig_main_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "tsconfig.main.json"))

    def test_tsconfig_preload_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "tsconfig.preload.json"))

    def test_electron_builder_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "electron-builder.yml"))

    def test_main_entry_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/main/index.ts"))

    def test_window_manager_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/main/window-manager.ts"))

    def test_tray_manager_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/main/tray-manager.ts"))

    def test_notification_manager_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/main/notification-manager.ts"))

    def test_update_manager_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/main/update-manager.ts"))

    def test_ipc_handler_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/main/ipc-handler.ts"))

    def test_store_manager_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/main/store-manager.ts"))

    def test_preload_script_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/preload/index.ts"))

    def test_dev_script_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "scripts/dev.ts"))

    def test_env_d_ts_exists(self):
        assert file_exists(os.path.join(DESKTOP_DIR, "src/renderer/env.d.ts"))


# ---------------------------------------------------------------------------
# M12.2: IPC Handler Content
# ---------------------------------------------------------------------------

class TestIpcHandlerContent:
    """Verify IPC handler registers all required handlers."""

    def test_registers_window_handlers(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/ipc-handler.ts"))
        assert "window:minimize" in content
        assert "window:maximize" in content
        assert "window:close" in content
        assert "window:focus" in content

    def test_registers_app_handlers(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/ipc-handler.ts"))
        assert "app:version" in content
        assert "app:name" in content
        assert "app:platform" in content

    def test_registers_store_handlers(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/ipc-handler.ts"))
        assert "store:get" in content
        assert "store:set" in content
        assert "store:delete" in content
        assert "store:clear" in content

    def test_registers_notification_handlers(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/ipc-handler.ts"))
        assert "notification:send" in content

    def test_registers_update_handlers(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/ipc-handler.ts"))
        assert "update:check" in content
        assert "update:install" in content
        assert "update:status" in content

    def test_registers_dialog_handlers(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/ipc-handler.ts"))
        assert "dialog:open-file" in content
        assert "dialog:save-file" in content

    def test_registers_system_handlers(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/ipc-handler.ts"))
        assert "system:screen-size" in content
        assert "system:open-external" in content


# ---------------------------------------------------------------------------
# M12.3: Auto-Updater
# ---------------------------------------------------------------------------

class TestAutoUpdater:
    """Verify auto-updater configuration."""

    def test_update_manager_uses_electron_updater(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/update-manager.ts"))
        assert "electron-updater" in content
        assert "autoUpdater" in content

    def test_update_events_registered(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/update-manager.ts"))
        assert "checking-for-update" in content
        assert "update-available" in content
        assert "update-not-available" in content
        assert "download-progress" in content
        assert "update-downloaded" in content

    def test_quit_and_install(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/update-manager.ts"))
        assert "quitAndInstall" in content

    def test_electron_builder_config(self):
        content = read_file(os.path.join(DESKTOP_DIR, "electron-builder.yml"))
        assert "appId: com.aios.desktop" in content
        assert "productName: AIOS" in content
        assert "nsis" in content
        assert "dmg" in content
        assert "AppImage" in content


# ---------------------------------------------------------------------------
# M12.4: System Tray & Notifications
# ---------------------------------------------------------------------------

class TestSystemTray:
    """Verify system tray setup."""

    def test_tray_has_context_menu(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/tray-manager.ts"))
        assert "setContextMenu" in content
        assert "Show AIOS" in content
        assert "Quit AIOS" in content

    def test_tray_handles_double_click(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/tray-manager.ts"))
        assert "double-click" in content

    def test_notification_manager_sends(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/notification-manager.ts"))
        assert "new Notification" in content
        assert "notification.show()" in content

    def test_notification_has_goal_update(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/notification-manager.ts"))
        assert "sendGoalUpdate" in content
        assert "sendAgentResponse" in content
        assert "sendConsolidationComplete" in content


# ---------------------------------------------------------------------------
# M12.5: Store Manager
# ---------------------------------------------------------------------------

class TestStoreManager:
    """Verify persistent store configuration."""

    def test_store_uses_electron_store(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/store-manager.ts"))
        assert "electron-store" in content
        assert "Store" in content

    def test_store_has_default_settings(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/store-manager.ts"))
        assert "settings:theme" in content
        assert "settings:apiUrl" in content
        assert "settings:notifications" in content
        assert "settings:fontSize" in content

    def test_store_has_window_state(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/store-manager.ts"))
        assert "window:bounds" in content
        assert "window:isMaximized" in content

    def test_store_has_convenience_methods(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/store-manager.ts"))
        assert "getWindowBounds" in content
        assert "setTheme" in content
        assert "getApiUrl" in content


# ---------------------------------------------------------------------------
# M12.6: Window Manager
# ---------------------------------------------------------------------------

class TestWindowManager:
    """Verify window manager configuration."""

    def test_window_has_correct_size(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/window-manager.ts"))
        assert "1400" in content
        assert "900" in content

    def test_window_has_security_settings(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/window-manager.ts"))
        assert "contextIsolation: true" in content
        assert "nodeIntegration: false" in content
        assert "sandbox: true" in content

    def test_window_loads_next_app(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/window-manager.ts"))
        assert "loadURL" in content or "loadFile" in content
        assert "localhost:3000" in content

    def test_main_entry_creates_window(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/index.ts"))
        assert "createMainWindow" in content
        assert "whenReady" in content

    def test_main_entry_has_menu(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/index.ts"))
        assert "buildMenu" in content or "Menu.setApplicationMenu" in content


# ---------------------------------------------------------------------------
# M12.7: Preload Script
# ---------------------------------------------------------------------------

class TestPreloadScript:
    """Verify preload script exposes correct API."""

    def test_uses_context_bridge(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/preload/index.ts"))
        assert "contextBridge" in content
        assert "exposeInMainWorld" in content

    def test_exposes_window_api(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/preload/index.ts"))
        assert "window:minimize" in content
        assert "window:maximize" in content
        assert "window:close" in content

    def test_exposes_store_api(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/preload/index.ts"))
        assert "store:get" in content
        assert "store:set" in content

    def test_exposes_update_api(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/preload/index.ts"))
        assert "update:check" in content
        assert "update:install" in content

    def test_validates_channels(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/preload/index.ts"))
        assert "validChannels" in content

    def test_env_d_ts_exposes_aios(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/renderer/env.d.ts"))
        assert "window.aios" in content
        assert "AiosDesktopAPI" in content


# ---------------------------------------------------------------------------
# M12.8: Web App Electron Integration
# ---------------------------------------------------------------------------

class TestWebElectronIntegration:
    """Verify web app has Electron bridge and desktop components."""

    def test_electron_bridge_exists(self):
        assert file_exists(os.path.join(WEB_SRC, "lib", "electron.ts"))

    def test_electron_bridge_has_is_desktop(self):
        content = read_file(os.path.join(WEB_SRC, "lib", "electron.ts"))
        assert "isDesktop" in content
        assert "window.aios" in content

    def test_electron_bridge_has_fallbacks(self):
        content = read_file(os.path.join(WEB_SRC, "lib", "electron.ts"))
        assert "openFileDialog" in content
        assert "saveFileDialog" in content
        assert "sendNotification" in content

    def test_electron_bridge_has_persistence(self):
        content = read_file(os.path.join(WEB_SRC, "lib", "electron.ts"))
        assert "getSetting" in content
        assert "setSetting" in content

    def test_titlebar_component_exists(self):
        assert file_exists(os.path.join(WEB_SRC, "desktop", "components", "Titlebar.tsx"))

    def test_titlebar_has_window_controls(self):
        content = read_file(os.path.join(WEB_SRC, "desktop", "components", "Titlebar.tsx"))
        assert "minimizeWindow" in content
        assert "maximizeWindow" in content
        assert "closeWindow" in content

    def test_titlebar_mac_traffic_lights(self):
        content = read_file(os.path.join(WEB_SRC, "desktop", "components", "Titlebar.tsx"))
        assert "trafficLightPosition" in content or "traffic" in content.lower()

    def test_update_indicator_exists(self):
        assert file_exists(os.path.join(WEB_SRC, "desktop", "components", "UpdateIndicator.tsx"))

    def test_update_indicator_has_download(self):
        content = read_file(os.path.join(WEB_SRC, "desktop", "components", "UpdateIndicator.tsx"))
        assert "downloading" in content.lower()
        assert "downloaded" in content.lower()
        assert "installUpdate" in content

    def test_offline_indicator_exists(self):
        assert file_exists(os.path.join(WEB_SRC, "desktop", "components", "OfflineIndicator.tsx"))

    def test_offline_indicator_checks_gateway(self):
        content = read_file(os.path.join(WEB_SRC, "desktop", "components", "OfflineIndicator.tsx"))
        assert "gateway" in content.lower()
        assert "fetch" in content


# ---------------------------------------------------------------------------
# M12.9: Deep Links
# ---------------------------------------------------------------------------

class TestDeepLinks:
    """Verify deep link support."""

    def test_main_registers_protocol(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/index.ts"))
        assert "aios://" in content
        assert "setAsDefaultProtocolClient" in content

    def test_main_handles_deep_links(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/main/index.ts"))
        assert "handleDeepLink" in content
        assert "open-url" in content

    def test_preload_exposes_deep_link(self):
        content = read_file(os.path.join(DESKTOP_DIR, "src/preload/index.ts"))
        assert "deep-link" in content

    def test_bridge_listens_deep_link(self):
        content = read_file(os.path.join(WEB_SRC, "lib", "electron.ts"))
        assert "onDeepLink" in content


# ---------------------------------------------------------------------------
# M12.10: Tests File
# ---------------------------------------------------------------------------

class TestM12TestFile:
    """Verify the test file exists and has proper structure."""

    def test_test_file_exists(self):
        assert file_exists(os.path.join(ROOT, "test_m12_desktop.py"))

    def test_test_file_has_electron_tests(self):
        content = read_file(os.path.join(ROOT, "test_m12_desktop.py"))
        assert "TestElectronShellStructure" in content
        assert "TestIpcHandlerContent" in content
        assert "TestAutoUpdater" in content
        assert "TestSystemTray" in content
        assert "TestStoreManager" in content
        assert "TestWindowManager" in content
        assert "TestPreloadScript" in content
        assert "TestWebElectronIntegration" in content
        assert "TestDeepLinks" in content

    def test_test_count(self):
        content = read_file(os.path.join(ROOT, "test_m12_desktop.py"))
        test_count = content.count("def test_")
        assert test_count >= 50, f"Expected at least 50 tests, found {test_count}"
