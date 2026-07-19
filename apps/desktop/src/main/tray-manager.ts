/**
 * TrayManager — System tray with context menu.
 */

import { Tray, Menu, nativeImage, BrowserWindow, app } from "electron";
import path from "path";

export class TrayManager {
  private tray: Tray | null = null;

  createTray(mainWindow: BrowserWindow) {
    // Create tray icon (16x16 for macOS menu bar)
    const iconPath = this.getIconPath();
    let trayIcon: nativeImage;

    try {
      trayIcon = nativeImage.createFromPath(iconPath);
      trayIcon = trayIcon.resize({ width: 16, height: 16 });
    } catch {
      // Fallback: create a simple colored icon
      trayIcon = nativeImage.createEmpty();
    }

    this.tray = new Tray(trayIcon);
    this.tray.setToolTip("AIOS — AI Operating System");

    const contextMenu = Menu.buildFromTemplate([
      {
        label: "Show AIOS",
        click: () => {
          mainWindow.show();
          mainWindow.focus();
        },
      },
      { type: "separator" },
      {
        label: "Conversation",
        click: () => {
          mainWindow.show();
          mainWindow.webContents.send("navigate", "conversation");
        },
      },
      {
        label: "Goals",
        click: () => {
          mainWindow.show();
          mainWindow.webContents.send("navigate", "goals");
        },
      },
      {
        label: "Memory Explorer",
        click: () => {
          mainWindow.show();
          mainWindow.webContents.send("navigate", "memory-explorer");
        },
      },
      { type: "separator" },
      {
        label: "Check for Updates…",
        click: () => {
          mainWindow.webContents.send("check-for-updates");
        },
      },
      { type: "separator" },
      {
        label: "Quit AIOS",
        click: () => {
          app.quit();
        },
      },
    ]);

    this.tray.setContextMenu(contextMenu);

    // Double-click to show window
    this.tray.on("double-click", () => {
      mainWindow.show();
      mainWindow.focus();
    });

    return this.tray;
  }

  private getIconPath(): string {
    const isDev = !app.isPackaged;
    if (isDev) {
      return path.join(__dirname, "../../assets/trayIcon.png");
    }
    return path.join(process.resourcesPath, "assets/trayIcon.png");
  }

  updateBadge(count: number) {
    if (process.platform === "darwin") {
      app.setBadgeCount(count);
    }
  }

  destroy() {
    this.tray?.destroy();
    this.tray = null;
  }
}
