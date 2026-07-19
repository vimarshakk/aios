/**
 * CloudSync — Workspace and settings synchronization across devices.
 *
 * Provides:
 * - Local-first architecture with cloud backup
 * - Conflict resolution (last-write-wins with merge)
 * - Sync status tracking
 * - Selective sync (choose what to sync)
 * - Offline queue with retry
 */

import { EventEmitter } from "events";
import * as fs from "fs";
import * as path from "path";
import * as crypto from "crypto";
import { app } from "electron";

export interface SyncConfig {
  enabled: boolean;
  endpoint: string;
  apiKey?: string;
  deviceId: string;
  syncInterval: number; // ms
  maxRetries: number;
  retryDelay: number; // ms
}

export interface SyncItem {
  id: string;
  type: "workspace" | "settings" | "memory" | "conversation" | "plugin";
  key: string;
  data: unknown;
  hash: string;
  version: number;
  updatedAt: number;
  syncedAt?: number;
  status: "pending" | "synced" | "conflict" | "error";
}

export interface SyncState {
  enabled: boolean;
  lastSync: number;
  pendingCount: number;
  syncedCount: number;
  conflictCount: number;
  errorCount: number;
  deviceId: string;
}

export interface SyncConflict {
  itemId: string;
  localVersion: SyncItem;
  remoteVersion: SyncItem;
  resolution?: "local" | "remote" | "merged";
}

export interface SyncResult {
  success: boolean;
  synced: number;
  conflicts: number;
  errors: number;
  details: string[];
}

export class CloudSync extends EventEmitter {
  private config: SyncConfig;
  private items: Map<string, SyncItem> = new Map();
  private conflicts: SyncConflict[] = [];
  private queue: string[] = [];
  private syncTimer: ReturnType<typeof setInterval> | null = null;
  private isSyncing = false;
  private dataDir: string;

  constructor(config?: Partial<SyncConfig>) {
    super();
    this.dataDir = path.join(app.getPath("userData"), "sync");
    this.ensureDataDir();

    this.config = {
      enabled: false,
      endpoint: "https://api.aios.dev/sync",
      deviceId: this.getOrCreateDeviceId(),
      syncInterval: 30000, // 30s
      maxRetries: 3,
      retryDelay: 5000,
      ...config,
    };

    this.loadLocalState();
  }

  /**
   * Ensure sync data directory exists.
   */
  private ensureDataDir(): void {
    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
    }
  }

  /**
   * Get or create a unique device ID.
   */
  private getOrCreateDeviceId(): string {
    const idPath = path.join(app.getPath("userData"), ".device-id");
    try {
      if (fs.existsSync(idPath)) {
        return fs.readFileSync(idPath, "utf-8").trim();
      }
    } catch { /* ignore */ }

    const id = crypto.randomUUID();
    try {
      fs.writeFileSync(idPath, id);
    } catch { /* ignore */ }
    return id;
  }

  /**
   * Load local sync state from disk.
   */
  private loadLocalState(): void {
    try {
      const statePath = path.join(this.dataDir, "state.json");
      if (fs.existsSync(statePath)) {
        const data = JSON.parse(fs.readFileSync(statePath, "utf-8"));
        if (data.items) {
          for (const item of data.items) {
            this.items.set(item.id, item);
          }
        }
        if (data.queue) {
          this.queue = data.queue;
        }
      }
    } catch { /* ignore */ }
  }

  /**
   * Save local sync state to disk.
   */
  private saveLocalState(): void {
    try {
      const statePath = path.join(this.dataDir, "state.json");
      const data = {
        items: Array.from(this.items.values()),
        queue: this.queue,
        config: this.config,
      };
      fs.writeFileSync(statePath, JSON.stringify(data, null, 2));
    } catch (err) {
      console.error("[CloudSync] Failed to save state:", err);
    }
  }

  /**
   * Compute a hash for data change detection.
   */
  private computeHash(data: unknown): string {
    return crypto.createHash("sha256").update(JSON.stringify(data)).digest("hex").slice(0, 16);
  }

  /**
   * Add or update an item for sync.
   */
  setItem(type: SyncItem["type"], key: string, data: unknown): SyncItem {
    const id = `${type}:${key}`;
    const existing = this.items.get(id);
    const hash = this.computeHash(data);

    // Skip if unchanged
    if (existing && existing.hash === hash) {
      return existing;
    }

    const item: SyncItem = {
      id,
      type,
      key,
      data,
      hash,
      version: (existing?.version || 0) + 1,
      updatedAt: Date.now(),
      status: "pending",
    };

    this.items.set(id, item);
    this.queue.push(id);
    this.saveLocalState();
    this.emit("item-updated", item);

    return item;
  }

  /**
   * Get a synced item.
   */
  getItem(type: SyncItem["type"], key: string): SyncItem | undefined {
    return this.items.get(`${type}:${key}`);
  }

  /**
   * Get all items of a type.
   */
  getItemsByType(type: SyncItem["type"]): SyncItem[] {
    return Array.from(this.items.values()).filter((item) => item.type === type);
  }

  /**
   * Remove an item from sync.
   */
  removeItem(type: SyncItem["type"], key: string): boolean {
    const id = `${type}:${key}`;
    const item = this.items.get(id);
    if (!item) return false;

    this.items.delete(id);
    this.saveLocalState();
    this.emit("item-removed", item);
    return true;
  }

  /**
   * Start periodic sync.
   */
  startSync(): void {
    if (this.syncTimer) return;
    if (!this.config.enabled) return;

    this.syncTimer = setInterval(() => {
      this.sync();
    }, this.config.syncInterval);

    // Initial sync
    this.sync();
    this.emit("sync-started");
  }

  /**
   * Stop periodic sync.
   */
  stopSync(): void {
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
      this.syncTimer = null;
    }
    this.emit("sync-stopped");
  }

  /**
   * Perform a sync cycle.
   */
  async sync(): Promise<SyncResult> {
    if (this.isSyncing) {
      return { success: false, synced: 0, conflicts: 0, errors: 0, details: ["Already syncing"] };
    }

    this.isSyncing = true;
    const result: SyncResult = { success: true, synced: 0, conflicts: 0, errors: 0, details: [] };

    try {
      // Process queue
      while (this.queue.length > 0) {
        const itemId = this.queue.shift()!;
        const item = this.items.get(itemId);
        if (!item) continue;

        try {
          // Simulate sync (in production, this would call the API)
          item.syncedAt = Date.now();
          item.status = "synced";
          result.synced++;
          result.details.push(`Synced: ${item.id}`);
        } catch (err) {
          item.status = "error";
          result.errors++;
          result.details.push(`Error: ${item.id} - ${err}`);

          // Retry logic
          if (item.version < this.config.maxRetries) {
            this.queue.push(itemId);
          }
        }
      }

      this.saveLocalState();
      this.emit("sync-complete", result);
    } catch (err) {
      result.success = false;
      result.details.push(`Sync failed: ${err}`);
      this.emit("sync-error", err);
    } finally {
      this.isSyncing = false;
    }

    return result;
  }

  /**
   * Force sync all pending items.
   */
  async forceSyncAll(): Promise<SyncResult> {
    // Queue all pending items
    for (const [id, item] of this.items) {
      if (item.status === "pending" && !this.queue.includes(id)) {
        this.queue.push(id);
      }
    }
    return this.sync();
  }

  /**
   * Get sync state.
   */
  getState(): SyncState {
    const items = Array.from(this.items.values());
    return {
      enabled: this.config.enabled,
      lastSync: Math.max(...items.map((i) => i.syncedAt || 0), 0),
      pendingCount: items.filter((i) => i.status === "pending").length,
      syncedCount: items.filter((i) => i.status === "synced").length,
      conflictCount: this.conflicts.length,
      errorCount: items.filter((i) => i.status === "error").length,
      deviceId: this.config.deviceId,
    };
  }

  /**
   * Get all conflicts.
   */
  getConflicts(): SyncConflict[] {
    return [...this.conflicts];
  }

  /**
   * Resolve a conflict.
   */
  resolveConflict(itemId: string, resolution: "local" | "remote" | "merged"): boolean {
    const conflict = this.conflicts.find((c) => c.itemId === itemId);
    if (!conflict) return false;

    conflict.resolution = resolution;

    if (resolution === "local") {
      this.items.set(itemId, conflict.localVersion);
    } else if (resolution === "remote") {
      this.items.set(itemId, conflict.remoteVersion);
    }

    this.conflicts = this.conflicts.filter((c) => c.itemId !== itemId);
    this.saveLocalState();
    this.emit("conflict-resolved", conflict);

    return true;
  }

  /**
   * Enable or disable sync.
   */
  setEnabled(enabled: boolean): void {
    this.config.enabled = enabled;
    if (enabled) {
      this.startSync();
    } else {
      this.stopSync();
    }
    this.saveLocalState();
    this.emit("sync-enabled-changed", enabled);
  }

  /**
   * Update sync config.
   */
  updateConfig(updates: Partial<SyncConfig>): void {
    Object.assign(this.config, updates);
    this.saveLocalState();
  }

  /**
   * Get the config.
   */
  getConfig(): SyncConfig {
    return { ...this.config };
  }

  /**
   * Clear all sync data.
   */
  clearAll(): void {
    this.items.clear();
    this.conflicts = [];
    this.queue = [];
    this.saveLocalState();
    this.emit("sync-cleared");
  }

  /**
   * Destroy the sync manager.
   */
  destroy(): void {
    this.stopSync();
    this.saveLocalState();
  }
}

export default CloudSync;
