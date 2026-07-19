/**
 * WindowManager — Creates and manages BrowserWindow instances.
 */

import { BrowserWindow, screen } from "electron";
import path from "path";

export interface WindowManagerOptions {
  isDev: boolean;
  API_BASE: string;
}

export class WindowManager {
  private mainWindow: BrowserWindow | null = null;
  private options: WindowManagerOptions;

  constructor(options: WindowManagerOptions) {
    this.options = options;
  }

  getMainWindow(): BrowserWindow | null {
    return this.mainWindow;
  }

  createMainWindow(): BrowserWindow {
    if (this.mainWindow) {
      this.mainWindow.show();
      return this.mainWindow;
    }

    const { width, height } = screen.getPrimaryDisplay().workAreaSize;

    this.mainWindow = new BrowserWindow({
      width: Math.min(1400, width),
      height: Math.min(900, height),
      minWidth: 800,
      minHeight: 600,
      title: "AIOS",
      titleBarStyle: "hiddenInset",
      trafficLightPosition: { x: 16, y: 16 },
      backgroundColor: "#0a0a0a",
      show: false,
      webPreferences: {
        preload: path.join(__dirname, "../preload/index.js"),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
        webviewTag: false,
        spellcheck: true,
      },
    });

    // Show window when ready
    this.mainWindow.once("ready-to-show", () => {
      this.mainWindow?.show();
    });

    // Load the web app
    if (this.options.isDev) {
      this.mainWindow.loadURL("http://localhost:3000");
      this.mainWindow.webContents.openDevTools({ mode: "detach" });
    } else {
      this.mainWindow.loadFile(path.join(__dirname, "../out/index.html"));
    }

    // Handle external links
    this.mainWindow.webContents.setWindowOpenHandler(({ url }) => {
      if (url.startsWith("http")) {
        require("electron").shell.openExternal(url);
      }
      return { action: "deny" };
    });

    // Track window state
    this.mainWindow.on("closed", () => {
      this.mainWindow = null;
    });

    // Prevent new windows
    this.mainWindow.webContents.on("will-navigate", (event) => {
      event.preventDefault();
    });

    return this.mainWindow;
  }

  createSettingsWindow(): BrowserWindow {
    const settingsWindow = new BrowserWindow({
      width: 600,
      height: 500,
      parent: this.mainWindow!,
      modal: true,
      title: "Settings",
      resizable: false,
      backgroundColor: "#0a0a0a",
      webPreferences: {
        preload: path.join(__dirname, "../preload/index.js"),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });

    if (this.options.isDev) {
      settingsWindow.loadURL("http://localhost:3000/settings");
    } else {
      settingsWindow.loadFile(path.join(__dirname, "../out/index.html"));
    }

    return settingsWindow;
  }

  minimize() {
    this.mainWindow?.minimize();
  }

  maximize() {
    if (this.mainWindow?.isMaximized()) {
      this.mainWindow.unmaximize();
    } else {
      this.mainWindow?.maximize();
    }
  }

  close() {
    this.mainWindow?.close();
  }

  focus() {
    this.mainWindow?.focus();
  }

  isVisible(): boolean {
    return this.mainWindow?.isVisible() ?? false;
  }
}
