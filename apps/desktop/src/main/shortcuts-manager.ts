/**
 * ShortcutsManager — Global and app-scoped keyboard shortcuts.
 *
 * Provides:
 * - Global shortcuts (work even when app is not focused)
 * - App shortcuts (work when app is focused)
 * - Command palette (Cmd+K / Ctrl+K)
 * - Configurable shortcuts via settings
 */

import { globalShortcut, BrowserWindow } from "electron";

export interface ShortcutConfig {
  id: string;
  accelerator: string;
  label: string;
  global: boolean;
  enabled: boolean;
}

export interface ShortcutHandler {
  (window: BrowserWindow | null): void;
}

// Default shortcuts
const DEFAULT_SHORTCUTS: ShortcutConfig[] = [
  {
    id: "command-palette",
    accelerator: "CmdOrCtrl+K",
    label: "Command Palette",
    global: false,
    enabled: true,
  },
  {
    id: "memory-explorer",
    accelerator: "CmdOrCtrl+Shift+E",
    label: "Memory Explorer",
    global: false,
    enabled: true,
  },
  {
    id: "new-conversation",
    accelerator: "CmdOrCtrl+N",
    label: "New Conversation",
    global: false,
    enabled: true,
  },
  {
    id: "focus-search",
    accelerator: "CmdOrCtrl+/",
    label: "Focus Search",
    global: false,
    enabled: true,
  },
  {
    id: "toggle-sidebar",
    accelerator: "CmdOrCtrl+B",
    label: "Toggle Sidebar",
    global: false,
    enabled: true,
  },
  {
    id: "quick-remember",
    accelerator: "CmdOrCtrl+Shift+R",
    label: "Quick Remember",
    global: false,
    enabled: true,
  },
  {
    id: "show-hide",
    accelerator: "CmdOrCtrl+Shift+Space",
    label: "Show/Hide Window",
    global: true,
    enabled: true,
  },
];

export class ShortcutsManager {
  private shortcuts: Map<string, ShortcutConfig> = new Map();
  private handlers: Map<string, ShortcutHandler> = new Map();
  private mainWindow: BrowserWindow | null = null;

  constructor() {
    // Load default shortcuts
    for (const shortcut of DEFAULT_SHORTCUTS) {
      this.shortcuts.set(shortcut.id, { ...shortcut });
    }
  }

  setMainWindow(window: BrowserWindow) {
    this.mainWindow = window;
  }

  /**
   * Register all enabled shortcuts.
   */
  registerAll(): void {
    for (const [id, shortcut] of this.shortcuts) {
      if (shortcut.enabled) {
        this.registerOne(id, shortcut);
      }
    }
  }

  /**
   * Unregister all shortcuts.
   */
  unregisterAll(): void {
    globalShortcut.unregisterAll();
    this.handlers.clear();
  }

  /**
   * Register a single shortcut.
   */
  private registerOne(id: string, shortcut: ShortcutConfig): void {
    const handler = this.handlers.get(id);
    if (!handler) return;

    try {
      if (shortcut.global) {
        globalShortcut.register(shortcut.accelerator, () => {
          handler(this.mainWindow);
        });
      }
      // App-level shortcuts are registered via menu in index.ts
    } catch (err) {
      console.error(`[Shortcuts] Failed to register ${id}:`, err);
    }
  }

  /**
   * Register a handler for a shortcut.
   */
  on(id: string, handler: ShortcutHandler): void {
    this.handlers.set(id, handler);

    const shortcut = this.shortcuts.get(id);
    if (shortcut?.enabled) {
      this.registerOne(id, shortcut);
    }
  }

  /**
   * Update a shortcut's accelerator.
   */
  updateAccelerator(id: string, accelerator: string): void {
    const shortcut = this.shortcuts.get(id);
    if (!shortcut) return;

    // Unregister old
    if (shortcut.global) {
      globalShortcut.unregister(shortcut.accelerator);
    }

    // Update
    shortcut.accelerator = accelerator;
    this.shortcuts.set(id, shortcut);

    // Re-register
    if (shortcut.enabled) {
      this.registerOne(id, shortcut);
    }
  }

  /**
   * Enable/disable a shortcut.
   */
  setEnabled(id: string, enabled: boolean): void {
    const shortcut = this.shortcuts.get(id);
    if (!shortcut) return;

    shortcut.enabled = enabled;
    this.shortcuts.set(id, shortcut);

    if (enabled) {
      this.registerOne(id, shortcut);
    } else if (shortcut.global) {
      globalShortcut.unregister(shortcut.accelerator);
    }
  }

  /**
   * Get all shortcuts.
   */
  getAll(): ShortcutConfig[] {
    return Array.from(this.shortcuts.values());
  }

  /**
   * Get a specific shortcut.
   */
  get(id: string): ShortcutConfig | undefined {
    return this.shortcuts.get(id);
  }

  /**
   * Check if a shortcut is registered.
   */
  isRegistered(id: string): boolean {
    const shortcut = this.shortcuts.get(id);
    if (!shortcut) return false;
    return globalShortcut.isRegistered(shortcut.accelerator);
  }

  /**
   * Cleanup on app quit.
   */
  destroy(): void {
    this.unregisterAll();
  }
}

export default ShortcutsManager;
