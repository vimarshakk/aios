/**
 * WindowStatePersistence — Save and restore window bounds across sessions.
 */

import { BrowserWindow } from "electron";
import { StoreManager } from "./store-manager";

export class WindowStatePersistence {
  private storeManager: StoreManager;
  private window: BrowserWindow | null = null;
  private saveTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(storeManager: StoreManager) {
    this.storeManager = storeManager;
  }

  /**
   * Attach to a window to auto-save state.
   */
  attach(window: BrowserWindow): void {
    this.window = window;

    // Restore saved state
    this.restore(window);

    // Listen for changes
    window.on("resize", () => this.debouncedSave());
    window.on("move", () => this.debouncedSave());
    window.on("close", () => this.save());
  }

  /**
   * Restore window state from store.
   */
  restore(window: BrowserWindow): void {
    const bounds = this.storeManager.getWindowBounds();
    const isMaximized = this.storeManager.get("window:isMaximized");

    if (bounds) {
      window.setBounds(bounds);
    }

    if (isMaximized) {
      window.maximize();
    }
  }

  /**
   * Save current window state to store.
   */
  save(): void {
    if (!this.window || this.window.isDestroyed()) return;

    const bounds = this.window.getBounds();
    const isMaximized = this.window.isMaximized();

    this.storeManager.setWindowBounds(bounds);
    this.storeManager.set("window:isMaximized", isMaximized);
  }

  /**
   * Debounced save (avoid excessive writes during resize/move).
   */
  private debouncedSave(): void {
    if (this.saveTimer) clearTimeout(this.saveTimer);
    this.saveTimer = setTimeout(() => this.save(), 500);
  }

  /**
   * Cleanup.
   */
  destroy(): void {
    if (this.saveTimer) clearTimeout(this.saveTimer);
    this.window = null;
  }
}

export default WindowStatePersistence;
