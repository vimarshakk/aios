/**
 * WindowManager — Advanced window management with split view and multi-window.
 *
 * Extends the basic WindowManager to support:
 * - Split view (side-by-side panes)
 * - Multiple independent windows
 * - Window positioning and layout management
 * - Window grouping
 */

import { BrowserWindow, screen, BrowserWindowConstructorOptions } from "electron";
import * as path from "path";

export interface WindowConfig {
  id: string;
  url: string;
  title?: string;
  width?: number;
  height?: number;
  x?: number;
  y?: number;
  minWidth?: number;
  minHeight?: number;
  type?: "main" | "secondary" | "split" | "popup";
  parent?: string;
  group?: string;
}

export interface SplitLayout {
  direction: "horizontal" | "vertical";
  ratio: number; // 0-1, percentage for left/top pane
  left: WindowConfig;
  right: WindowConfig;
}

export interface WindowState {
  id: string;
  bounds: Electron.Rectangle;
  isMaximized: boolean;
  isMinimized: boolean;
  isVisible: boolean;
  type: string;
  group?: string;
}

export class AdvancedWindowManager {
  private windows: Map<string, BrowserWindow> = new Map();
  private windowConfigs: Map<string, WindowConfig> = new Map();
  private groups: Map<string, Set<string>> = new Map();
  private isDev: boolean;
  private apiBase: string;

  constructor(options: { isDev: boolean; apiBase: string }) {
    this.isDev = options.isDev;
    this.apiBase = options.apiBase;
  }

  /**
   * Create a new window.
   */
  createWindow(config: WindowConfig): BrowserWindow | null {
    // Check if window with this ID already exists
    if (this.windows.has(config.id)) {
      const existing = this.windows.get(config.id)!;
      existing.focus();
      return existing;
    }

    const options: BrowserWindowConstructorOptions = {
      width: config.width || 1200,
      height: config.height || 800,
      minWidth: config.minWidth || 400,
      minHeight: config.minHeight || 300,
      x: config.x,
      y: config.y,
      title: config.title || "AIOS",
      webPreferences: {
        preload: path.join(__dirname, "../preload/index.js"),
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: true,
      },
      show: false,
      trafficLightPosition: { x: 16, y: 16 },
      titleBarStyle: "hiddenInset",
      vibrancy: "under-window",
      visualEffectState: "active",
    };

    if (config.parent && this.windows.has(config.parent)) {
      options.parent = this.windows.get(config.parent);
    }

    const win = new BrowserWindow(options);

    // Load URL
    if (this.isDev) {
      win.loadURL(`${this.apiBase}${config.url}`);
    } else {
      win.loadFile(path.join(__dirname, `../renderer${config.url}`));
    }

    // Track window
    this.windows.set(config.id, win);
    this.windowConfigs.set(config.id, config);

    // Add to group if specified
    if (config.group) {
      this.addToGroup(config.id, config.group);
    }

    // Show when ready
    win.once("ready-to-show", () => {
      win.show();
    });

    // Cleanup on close
    win.on("closed", () => {
      this.windows.delete(config.id);
      this.windowConfigs.delete(config.id);
      if (config.group) {
        this.removeFromGroup(config.id, config.group);
      }
    });

    return win;
  }

  /**
   * Create a split view with two windows side by side.
   */
  createSplitView(layout: SplitLayout): { left: BrowserWindow; right: BrowserWindow } | null {
    const parentConfig = layout.left.parent ? this.windowConfigs.get(layout.left.parent) : undefined;
    const parentWidth = parentConfig?.width || 1600;
    const parentHeight = parentConfig?.height || 800;

    const leftWidth = Math.floor(parentWidth * layout.ratio);
    const rightWidth = parentWidth - leftWidth;

    let leftX: number | undefined;
    let rightX: number | undefined;

    if (layout.direction === "horizontal") {
      const bounds = this.getScreenBounds();
      leftX = bounds.x;
      rightX = bounds.x + leftWidth;
    }

    const leftConfig: WindowConfig = {
      ...layout.left,
      width: layout.direction === "horizontal" ? leftWidth : parentWidth,
      height: layout.direction === "vertical" ? Math.floor(parentHeight * layout.ratio) : parentHeight,
      x: leftX,
      y: layout.left.y,
      type: "split",
    };

    const rightConfig: WindowConfig = {
      ...layout.right,
      width: layout.direction === "horizontal" ? rightWidth : parentWidth,
      height: layout.direction === "vertical" ? parentHeight - Math.floor(parentHeight * layout.ratio) : parentHeight,
      x: rightX,
      y: layout.right.y,
      type: "split",
    };

    const left = this.createWindow(leftConfig);
    const right = this.createWindow(rightConfig);

    if (left && right) {
      // Group them
      const groupId = `split-${Date.now()}`;
      this.addToGroup(leftConfig.id, groupId);
      this.addToGroup(rightConfig.id, groupId);

      return { left, right };
    }

    return null;
  }

  /**
   * Get all open windows.
   */
  getAllWindows(): BrowserWindow[] {
    return Array.from(this.windows.values());
  }

  /**
   * Get a window by ID.
   */
  getWindow(id: string): BrowserWindow | undefined {
    return this.windows.get(id);
  }

  /**
   * Get window state.
   */
  getWindowState(id: string): WindowState | null {
    const win = this.windows.get(id);
    const config = this.windowConfigs.get(id);
    if (!win || !config) return null;

    return {
      id,
      bounds: win.getBounds(),
      isMaximized: win.isMaximized(),
      isMinimized: win.isMinimized(),
      isVisible: win.isVisible(),
      type: config.type || "main",
      group: config.group,
    };
  }

  /**
   * Get all window states.
   */
  getAllWindowStates(): WindowState[] {
    const states: WindowState[] = [];
    for (const id of this.windows.keys()) {
      const state = this.getWindowState(id);
      if (state) states.push(state);
    }
    return states;
  }

  /**
   * Close a window by ID.
   */
  closeWindow(id: string): boolean {
    const win = this.windows.get(id);
    if (!win) return false;
    win.close();
    return true;
  }

  /**
   * Focus a window by ID.
   */
  focusWindow(id: string): boolean {
    const win = this.windows.get(id);
    if (!win) return false;
    win.focus();
    return true;
  }

  /**
   * Minimize a window by ID.
   */
  minimizeWindow(id: string): boolean {
    const win = this.windows.get(id);
    if (!win) return false;
    win.minimize();
    return true;
  }

  /**
   * Maximize a window by ID.
   */
  maximizeWindow(id: string): boolean {
    const win = this.windows.get(id);
    if (!win) return false;
    if (win.isMaximized()) {
      win.unmaximize();
    } else {
      win.maximize();
    }
    return true;
  }

  /**
   * Tile windows side by side.
   */
  tileWindows(ids: string[], direction: "horizontal" | "vertical" = "horizontal"): boolean {
    const windows = ids.map((id) => this.windows.get(id)).filter(Boolean) as BrowserWindow[];
    if (windows.length < 2) return false;

    const bounds = this.getScreenBounds();
    const count = windows.length;

    if (direction === "horizontal") {
      const width = Math.floor(bounds.width / count);
      windows.forEach((win, i) => {
        win.setBounds({
          x: bounds.x + i * width,
          y: bounds.y,
          width,
          height: bounds.height,
        });
      });
    } else {
      const height = Math.floor(bounds.height / count);
      windows.forEach((win, i) => {
        win.setBounds({
          x: bounds.x,
          y: bounds.y + i * height,
          width: bounds.width,
          height,
        });
      });
    }

    return true;
  }

  /**
   * Cascade windows diagonally.
   */
  cascadeWindows(ids?: string[]): boolean {
    const windowIds = ids || Array.from(this.windows.keys());
    const windows = windowIds.map((id) => this.windows.get(id)).filter(Boolean) as BrowserWindow[];
    if (windows.length === 0) return false;

    const bounds = this.getScreenBounds();
    const offset = 30;
    const width = 800;
    const height = 600;

    windows.forEach((win, i) => {
      const x = bounds.x + (i * offset) % (bounds.width - width);
      const y = bounds.y + (i * offset) % (bounds.height - height);
      win.setBounds({ x, y, width, height });
    });

    return true;
  }

  /**
   * Add a window to a group.
   */
  addToGroup(windowId: string, groupId: string): void {
    if (!this.groups.has(groupId)) {
      this.groups.set(groupId, new Set());
    }
    this.groups.get(groupId)!.add(windowId);
  }

  /**
   * Remove a window from a group.
   */
  removeFromGroup(windowId: string, groupId: string): void {
    const group = this.groups.get(groupId);
    if (group) {
      group.delete(windowId);
      if (group.size === 0) {
        this.groups.delete(groupId);
      }
    }
  }

  /**
   * Get all windows in a group.
   */
  getGroup(groupId: string): string[] {
    return Array.from(this.groups.get(groupId) || []);
  }

  /**
   * Close all windows in a group.
   */
  closeGroup(groupId: string): void {
    const group = this.groups.get(groupId);
    if (!group) return;
    for (const id of group) {
      this.closeWindow(id);
    }
    this.groups.delete(groupId);
  }

  /**
   * Get screen bounds.
   */
  private getScreenBounds(): Electron.Rectangle {
    const display = screen.getPrimaryDisplay();
    return display.workArea;
  }

  /**
   * Cleanup.
   */
  destroy(): void {
    for (const [id] of this.windows) {
      this.closeWindow(id);
    }
    this.windows.clear();
    this.windowConfigs.clear();
    this.groups.clear();
  }
}

export default AdvancedWindowManager;
