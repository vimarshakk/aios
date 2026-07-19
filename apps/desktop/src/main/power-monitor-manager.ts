/**
 * PowerMonitorManager — System power state detection.
 *
 * Detects:
 * - System idle state
 * - Power source changes (AC/battery)
 * - Sleep/wake events
 * - Screen lock/unlock
 *
 * Useful for:
 * - Pausing background tasks when on battery
 * - Auto-save before sleep
 * - Resuming consolidation after wake
 */

import { powerMonitor, BrowserWindow } from "electron";

export type PowerEvent =
  | "suspend"
  | "resume"
  | "on-battery"
  | "on-ac"
  | "idle-state-changed"
  | "screen-lock-changed";

export type PowerHandler = (event: PowerEvent, data?: unknown) => void;

export class PowerMonitorManager {
  private handlers: Map<PowerEvent, PowerHandler[]> = new Map();
  private mainWindow: BrowserWindow | null = null;
  private idleThreshold = 300; // 5 minutes in seconds

  constructor() {
    this.setupListeners();
  }

  setMainWindow(window: BrowserWindow) {
    this.mainWindow = window;
  }

  private setupListeners(): void {
    powerMonitor.on("suspend", () => {
      this.emit("suspend");
    });

    powerMonitor.on("resume", () => {
      this.emit("resume");
    });

    powerMonitor.on("battery-state-changed", (_event, state) => {
      if (state === "charging" || state === "discharging") {
        this.emit(state === "charging" ? "on-ac" : "on-battery");
      }
    });

    // Idle detection
    let idleCheckInterval: ReturnType<typeof setInterval> | null = null;

    const startIdleCheck = () => {
      if (idleCheckInterval) clearInterval(idleCheckInterval);
      idleCheckInterval = setInterval(() => {
        const idleTime = powerMonitor.getSystemIdleTime();
        const isIdle = idleTime >= this.idleThreshold;
        this.emit("idle-state-changed", { idle: isIdle, seconds: idleTime });
      }, 30000); // Check every 30 seconds
    };

    startIdleCheck();
  }

  /**
   * Register event handler.
   */
  on(event: PowerEvent, handler: PowerHandler): void {
    const handlers = this.handlers.get(event) ?? [];
    handlers.push(handler);
    this.handlers.set(event, handlers);
  }

  /**
   * Emit event to handlers.
   */
  private emit(event: PowerEvent, data?: unknown): void {
    const handlers = this.handlers.get(event) ?? [];
    for (const handler of handlers) {
      try {
        handler(event, data);
      } catch (err) {
        console.error(`[PowerMonitor] Handler error for ${event}:`, err);
      }
    }

    // Forward to renderer
    this.mainWindow?.webContents.send("power-event", { event, data });
  }

  /**
   * Get current power state.
   */
  getState(): {
    isOnBattery: boolean;
    batteryLevel?: number;
    idleTime: number;
  } {
    const batteryLevel = powerMonitor.getSystemIdleLevel();
    const idleTime = powerMonitor.getSystemIdleTime();
    return {
      isOnBattery: batteryLevel > 0,
      batteryLevel,
      idleTime,
    };
  }

  /**
   * Set idle threshold (seconds).
   */
  setIdleThreshold(seconds: number): void {
    this.idleThreshold = seconds;
  }

  /**
   * Cleanup.
   */
  destroy(): void {
    this.handlers.clear();
    this.mainWindow = null;
  }
}

export default PowerMonitorManager;
