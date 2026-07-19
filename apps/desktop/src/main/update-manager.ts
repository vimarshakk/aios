/**
 * UpdateManager — Auto-update via electron-updater.
 */

import { autoUpdater, UpdateInfo } from "electron-updater";
import { app, BrowserWindow } from "electron";
import path from "path";

export interface UpdateStatus {
  checking: boolean;
  available: boolean;
  downloaded: boolean;
  info: UpdateInfo | null;
  error: string | null;
}

export class UpdateManager {
  private status: UpdateStatus = {
    checking: false,
    available: false,
    downloaded: false,
    info: null,
    error: null,
  };
  private mainWindow: BrowserWindow | null = null;

  constructor() {
    // Configure auto-updater
    autoUpdater.autoDownload = true;
    autoUpdater.autoInstallOnAppQuit = true;
    autoUpdater.allowPrerelease = false;
    autoUpdater.allowDowngrade = false;

    // Use a temp directory for downloads
    autoUpdater.logger = {
      info: (msg: string) => console.log(`[Update] ${msg}`),
      warn: (msg: string) => console.warn(`[Update] ${msg}`),
      error: (msg: string) => console.error(`[Update] ${msg}`),
    };

    // Event handlers
    autoUpdater.on("checking-for-update", () => {
      this.status.checking = true;
      this.status.error = null;
      this.notifyRenderer("update:checking");
    });

    autoUpdater.on("update-available", (info: UpdateInfo) => {
      this.status.checking = false;
      this.status.available = true;
      this.status.info = info;
      this.notifyRenderer("update:available", { version: info.version, releaseDate: info.releaseDate });
    });

    autoUpdater.on("update-not-available", () => {
      this.status.checking = false;
      this.status.available = false;
      this.notifyRenderer("update:not-available");
    });

    autoUpdater.on("download-progress", (progress) => {
      this.notifyRenderer("update:progress", {
        percent: progress.percent,
        transferred: progress.transferred,
        total: progress.total,
      });
    });

    autoUpdater.on("update-downloaded", (info: UpdateInfo) => {
      this.status.downloaded = true;
      this.status.info = info;
      this.notifyRenderer("update:downloaded", { version: info.version });
    });

    autoUpdater.on("error", (err: Error) => {
      this.status.checking = false;
      this.status.error = err.message;
      this.notifyRenderer("update:error", { error: err.message });
    });
  }

  setMainWindow(window: BrowserWindow) {
    this.mainWindow = window;
  }

  checkForUpdates() {
    if (app.isPackaged) {
      autoUpdater.checkForUpdates().catch((err) => {
        console.error("[Update] Check failed:", err);
      });
    }
  }

  quitAndInstall() {
    autoUpdater.quitAndInstall(false, true);
  }

  getStatus(): UpdateStatus {
    return { ...this.status };
  }

  cancel() {
    // No explicit cancel method, but we can ignore future events
  }

  private notifyRenderer(channel: string, data?: unknown) {
    this.mainWindow?.webContents.send(channel, data);
  }
}
