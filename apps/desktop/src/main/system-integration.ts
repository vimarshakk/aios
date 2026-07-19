/**
 * SystemIntegration — Desktop system tray, notifications, Dock/Taskbar badges.
 *
 * Extends basic system tray with:
 * - Dock badge (macOS) / Taskbar badge (Windows)
 * - Badge count updates
 * - Progress bar in taskbar
 * - App icon overlay (Windows)
 * - Badge text (macOS)
 * - Unread indicator
 */

import { app, BrowserWindow, Tray, nativeImage, nativeTheme } from "electron";
import * as path from "path";

export interface BadgeOptions {
  count?: number;
  text?: string;
  color?: "red" | "green" | "yellow" | "blue";
}

export interface ProgressOptions {
  progress: number; // 0-1
  mode?: "none" | "normal" | "indeterminate" | "error" | "paused";
}

export interface TrayMenuItem {
  label: string;
  click?: () => void;
  type?: "normal" | "separator" | "checkbox" | "radio";
  checked?: boolean;
  enabled?: boolean;
  submenu?: TrayMenuItem[];
}

export class SystemIntegration {
  private tray: Tray | null = null;
  private badgeCount = 0;
  private progressValue = 0;
  private progressMode: ProgressOptions["mode"] = "none";

  /**
   * Initialize system integration with tray.
   */
  init(mainWindow: BrowserWindow): void {
    this.createTray(mainWindow);
  }

  /**
   * Create the system tray.
   */
  createTray(mainWindow: BrowserWindow): Tray {
    // Create tray icon
    const iconPath = this.getTrayIconPath();
    let icon: nativeImage;

    try {
      icon = nativeImage.createFromPath(iconPath);
    } catch {
      // Fallback: create a small blank icon
      icon = nativeImage.createEmpty();
    }

    // Resize for tray (macOS template images should be 16x16 or 22x22)
    if (process.platform === "darwin") {
      icon = icon.resize({ width: 22, height: 22 });
    }

    this.tray = new Tray(icon);
    this.tray.setToolTip("AIOS");

    // Show window on tray click
    this.tray.on("click", () => {
      if (mainWindow) {
        if (mainWindow.isVisible()) {
          mainWindow.focus();
        } else {
          mainWindow.show();
        }
      }
    });

    return this.tray;
  }

  /**
   * Get the tray icon path based on platform and theme.
   */
  private getTrayIconPath(): string {
    const isDark = nativeTheme.shouldUseDarkColors;
    const suffix = isDark ? "white" : "black";
    const ext = process.platform === "win32" ? ".ico" : ".png";
    return path.join(__dirname, `../../assets/tray-icon-${suffix}${ext}`);
  }

  /**
   * Set the Dock badge count (macOS).
   */
  setBadgeCount(count: number): void {
    this.badgeCount = count;
    if (process.platform === "darwin") {
      app.setBadgeCount(count);
    }
  }

  /**
   * Set the Dock badge text (macOS).
   */
  setBadgeText(text: string): void {
    if (process.platform === "darwin") {
      app.setBadgeText(text);
    }
  }

  /**
   * Set the Dock badge color (macOS).
   */
  setBadgeColor(color: BadgeOptions["color"] = "red"): void {
    if (process.platform === "darwin") {
      const colorMap: Record<string, string> = {
        red: "#FF3B30",
        green: "#34C759",
        yellow: "#FFCC00",
        blue: "#007AFF",
      };
      app.setBadgeColor(colorMap[color] || colorMap.red);
    }
  }

  /**
   * Update badge with count and optional color.
   */
  updateBadge(options: BadgeOptions): void {
    if (options.count !== undefined) {
      this.setBadgeCount(options.count);
    }
    if (options.text !== undefined) {
      this.setBadgeText(options.text);
    }
    if (options.color) {
      this.setBadgeColor(options.color);
    }
  }

  /**
   * Clear the badge.
   */
  clearBadge(): void {
    this.badgeCount = 0;
    this.setBadgeCount(0);
    this.setBadgeText("");
  }

  /**
   * Set taskbar/Dock progress bar.
   */
  setProgress(options: ProgressOptions, mainWindow?: BrowserWindow | null): void {
    this.progressValue = Math.max(0, Math.min(1, options.progress));
    this.progressMode = options.mode || "normal";

    if (mainWindow) {
      mainWindow.setProgressBar(this.progressValue, { mode: this.progressMode as any });
    }
  }

  /**
   * Clear the progress bar.
   */
  clearProgress(mainWindow?: BrowserWindow | null): void {
    this.progressValue = 0;
    this.progressMode = "none";

    if (mainWindow) {
      mainWindow.setProgressBar(-1); // -1 removes progress bar
    }
  }

  /**
   * Set app icon overlay (Windows taskbar).
   */
  setOverlayIcon(iconPath: string, description: string, mainWindow?: BrowserWindow | null): void {
    if (process.platform === "win32" && mainWindow) {
      const icon = nativeImage.createFromPath(iconPath);
      mainWindow.setOverlayIcon(icon, description);
    }
  }

  /**
   * Clear the overlay icon.
   */
  clearOverlayIcon(mainWindow?: BrowserWindow | null): void {
    if (process.platform === "win32" && mainWindow) {
      mainWindow.setOverlayIcon(null, "");
    }
  }

  /**
   * Flash the window (Windows taskbar).
   */
  flashFrame(flash: boolean, mainWindow?: BrowserWindow | null): void {
    mainWindow?.flashFrame(flash);
  }

  /**
   * Set the tray tooltip.
   */
  setToolTip(text: string): void {
    this.tray?.setToolTip(text);
  }

  /**
   * Update tray context menu.
   */
  setContextMenu(items: TrayMenuItem[]): void {
    if (!this.tray) return;

    const { Menu } = require("electron");
    const template = items.map((item) => this.convertMenuItem(item));
    this.tray.setContextMenu(Menu.buildFromTemplate(template));
  }

  /**
   * Convert TrayMenuItem to Electron MenuItemConstructorOptions.
   */
  private convertMenuItem(item: TrayMenuItem): any {
    const result: any = {
      label: item.label,
      type: item.type || "normal",
      checked: item.checked,
      enabled: item.enabled !== false,
    };

    if (item.click) {
      result.click = item.click;
    }

    if (item.submenu) {
      result.submenu = item.submenu.map((sub) => this.convertMenuItem(sub));
    }

    return result;
  }

  /**
   * Get current badge state.
   */
  getBadgeState(): { count: number; text: string } {
    return {
      count: this.badgeCount,
      text: this.badgeCount > 0 ? String(this.badgeCount) : "",
    };
  }

  /**
   * Get current progress state.
   */
  getProgressState(): { progress: number; mode: string } {
    return {
      progress: this.progressValue,
      mode: this.progressMode || "none",
    };
  }

  /**
   * Destroy tray and cleanup.
   */
  destroy(): void {
    this.tray?.destroy();
    this.tray = null;
    this.clearBadge();
  }
}

export default SystemIntegration;
