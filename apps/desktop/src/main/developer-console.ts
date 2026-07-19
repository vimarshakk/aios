/**
 * DeveloperConsole — In-app developer tools and console.
 *
 * Provides:
 * - Console log capture (main process logs forwarded to renderer)
 * - DevTools toggle
 * - App diagnostics (memory, CPU, disk)
 * - Environment info
 * - Performance metrics
 */

import { app, BrowserWindow, ipcMain } from "electron";
import * as os from "os";

export interface ConsoleEntry {
  id: string;
  timestamp: number;
  level: "log" | "warn" | "error" | "info" | "debug";
  source: "main" | "renderer" | "system";
  message: string;
  data?: unknown;
}

export interface AppDiagnostics {
  platform: string;
  arch: string;
  electronVersion: string;
  nodeVersion: string;
  chromeVersion: string;
  memoryUsage: NodeJS.MemoryUsage;
  uptime: number;
  cpuUsage: NodeJS.CpuUsage;
  systemMemory: {
    total: number;
    free: number;
    used: number;
  };
  appPath: string;
  userDataPath: string;
  isPackaged: boolean;
}

export interface PerformanceMetrics {
  heapUsed: number;
  heapTotal: number;
  rss: number;
  external: number;
  arrayBuffers: number;
  cpuUsage: NodeJS.CpuUsage;
  uptime: number;
}

export class DeveloperConsole {
  private logs: ConsoleEntry[] = [];
  private maxLogs = 1000;
  private logId = 0;
  private captureEnabled = false;
  private originalConsole = {
    log: console.log,
    warn: console.warn,
    error: console.error,
    info: console.info,
    debug: console.debug,
  };

  /**
   * Start capturing console output from main process.
   */
  startCapture(): void {
    if (this.captureEnabled) return;
    this.captureEnabled = true;

    const levels: Array<"log" | "warn" | "error" | "info" | "debug"> = ["log", "warn", "error", "info", "debug"];

    for (const level of levels) {
      const original = this.originalConsole[level];
      console[level] = (...args: unknown[]) => {
        original.apply(console, args);
        this.addLog(level, "main", args.map(String).join(" "));
      };
    }
  }

  /**
   * Stop capturing console output.
   */
  stopCapture(): void {
    if (!this.captureEnabled) return;
    this.captureEnabled = false;

    console.log = this.originalConsole.log;
    console.warn = this.originalConsole.warn;
    console.error = this.originalConsole.error;
    console.info = this.originalConsole.info;
    console.debug = this.originalConsole.debug;
  }

  /**
   * Add a log entry.
   */
  addLog(level: ConsoleEntry["level"], source: ConsoleEntry["source"], message: string, data?: unknown): ConsoleEntry {
    const entry: ConsoleEntry = {
      id: `log-${++this.logId}`,
      timestamp: Date.now(),
      level,
      source,
      message,
      data,
    };

    this.logs.push(entry);

    // Trim to max size
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs);
    }

    return entry;
  }

  /**
   * Get all captured logs.
   */
  getLogs(filter?: { level?: string; source?: string; search?: string }): ConsoleEntry[] {
    let result = [...this.logs];

    if (filter?.level) {
      result = result.filter((l) => l.level === filter.level);
    }
    if (filter?.source) {
      result = result.filter((l) => l.source === filter.source);
    }
    if (filter?.search) {
      const search = filter.search.toLowerCase();
      result = result.filter((l) => l.message.toLowerCase().includes(search));
    }

    return result;
  }

  /**
   * Clear all captured logs.
   */
  clearLogs(): void {
    this.logs = [];
  }

  /**
   * Get app diagnostics.
   */
  getDiagnostics(): AppDiagnostics {
    const memUsage = process.memoryUsage();
    const totalMem = os.totalmem();
    const freeMem = os.freemem();

    return {
      platform: process.platform,
      arch: process.arch,
      electronVersion: process.versions.electron || "unknown",
      nodeVersion: process.versions.node,
      chromeVersion: process.versions.chrome,
      memoryUsage: memUsage,
      uptime: process.uptime(),
      cpuUsage: process.cpuUsage(),
      systemMemory: {
        total: totalMem,
        free: freeMem,
        used: totalMem - freeMem,
      },
      appPath: app.getPath("exe"),
      userDataPath: app.getPath("userData"),
      isPackaged: app.isPackaged,
    };
  }

  /**
   * Get performance metrics.
   */
  getPerformanceMetrics(): PerformanceMetrics {
    const mem = process.memoryUsage();
    return {
      heapUsed: mem.heapUsed,
      heapTotal: mem.heapTotal,
      rss: mem.rss,
      external: mem.external,
      arrayBuffers: mem.arrayBuffers,
      cpuUsage: process.cpuUsage(),
      uptime: process.uptime(),
    };
  }

  /**
   * Toggle DevTools on a window.
   */
  toggleDevTools(win: BrowserWindow | null): void {
    if (!win) return;
    if (win.webContents.isDevToolsOpened()) {
      win.webContents.closeDevTools();
    } else {
      win.webContents.openDevTools();
    }
  }

  /**
   * Open DevTools.
   */
  openDevTools(win: BrowserWindow | null): void {
    win?.webContents.openDevTools();
  }

  /**
   * Close DevTools.
   */
  closeDevTools(win: BrowserWindow | null): void {
    win?.webContents.closeDevTools();
  }

  /**
   * Check if DevTools are open.
   */
  isDevToolsOpen(win: BrowserWindow | null): boolean {
    return win?.webContents.isDevToolsOpened() ?? false;
  }

  /**
   * Register IPC handlers for developer console.
   */
  registerIpcHandlers(win: BrowserWindow | null): void {
    ipcMain.handle("devconsole:logs", (_event, filter?) => {
      return this.getLogs(filter);
    });

    ipcMain.handle("devconsole:clear-logs", () => {
      this.clearLogs();
    });

    ipcMain.handle("devconsole:diagnostics", () => {
      return this.getDiagnostics();
    });

    ipcMain.handle("devconsole:performance", () => {
      return this.getPerformanceMetrics();
    });

    ipcMain.handle("devconsole:toggle-devtools", () => {
      this.toggleDevTools(win);
    });

    ipcMain.handle("devconsole:open-devtools", () => {
      this.openDevTools(win);
    });

    ipcMain.handle("devconsole:close-devtools", () => {
      this.closeDevTools(win);
    });

    ipcMain.handle("devconsole:is-devtools-open", () => {
      return this.isDevToolsOpen(win);
    });

    ipcMain.handle("devconsole:start-capture", () => {
      this.startCapture();
    });

    ipcMain.handle("devconsole:stop-capture", () => {
      this.stopCapture();
    });

    ipcMain.handle("devconsole:is-capturing", () => {
      return this.captureEnabled;
    });
  }

  /**
   * Cleanup.
   */
  destroy(): void {
    this.stopCapture();
    this.logs = [];
  }
}

export default DeveloperConsole;
