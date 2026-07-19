/**
 * Persistence — Durable state management for crash recovery.
 *
 * Provides:
 * - Goal/task state persistence (resume after reboot)
 * - Crash recovery with checkpoint system
 * - Durable task queues
 * - Execution history archival
 * - State versioning and migration
 */

import { EventEmitter } from "events";
import * as fs from "fs";
import * as path from "path";
import * as crypto from "crypto";
import { app } from "electron";

export interface Checkpoint {
  id: string;
  timestamp: number;
  type: "goal" | "task" | "workflow" | "full";
  entityId: string;
  state: unknown;
  checksum: string;
  version: number;
}

export interface QueueItem<T = unknown> {
  id: string;
  queue: string;
  payload: T;
  priority: number;
  enqueuedAt: number;
  dequeuedAt?: number;
  status: "pending" | "processing" | "completed" | "failed";
  retryCount: number;
  maxRetries: number;
  error?: string;
}

export interface HistoryEntry {
  id: string;
  entityType: "goal" | "task" | "workflow";
  entityId: string;
  action: string;
  timestamp: number;
  snapshot: unknown;
}

export interface PersistenceConfig {
  dataDir: string;
  maxCheckpoints: number;
  maxHistory: number;
  checkpointInterval: number; // ms
  autoSave: boolean;
}

export class Persistence extends EventEmitter {
  private config: PersistenceConfig;
  private checkpoints: Checkpoint[] = [];
  private queues: Map<string, QueueItem[]> = new Map();
  private history: HistoryEntry[] = [];
  private stateVersion: number = 1;
  private checkpointTimer: ReturnType<typeof setInterval> | null = null;

  constructor(config?: Partial<PersistenceConfig>) {
    super();
    this.config = {
      dataDir: path.join(app.getPath("userData"), "persistence"),
      maxCheckpoints: 100,
      maxHistory: 10000,
      checkpointInterval: 60000, // 1 minute
      autoSave: true,
      ...config,
    };

    this.ensureDataDir();
    this.loadState();
  }

  private ensureDataDir(): void {
    if (!fs.existsSync(this.config.dataDir)) {
      fs.mkdirSync(this.config.dataDir, { recursive: true });
    }
  }

  private loadState(): void {
    try {
      const checkpointsPath = path.join(this.config.dataDir, "checkpoints.json");
      if (fs.existsSync(checkpointsPath)) {
        this.checkpoints = JSON.parse(fs.readFileSync(checkpointsPath, "utf-8"));
      }

      const queuesPath = path.join(this.config.dataDir, "queues.json");
      if (fs.existsSync(queuesPath)) {
        const data = JSON.parse(fs.readFileSync(queuesPath, "utf-8"));
        for (const [key, value] of Object.entries(data)) {
          this.queues.set(key, value as QueueItem[]);
        }
      }

      const historyPath = path.join(this.config.dataDir, "history.json");
      if (fs.existsSync(historyPath)) {
        this.history = JSON.parse(fs.readFileSync(historyPath, "utf-8"));
      }

      const versionPath = path.join(this.config.dataDir, "version.json");
      if (fs.existsSync(versionPath)) {
        const data = JSON.parse(fs.readFileSync(versionPath, "utf-8"));
        this.stateVersion = data.version || 1;
      }
    } catch { /* ignore */ }
  }

  private saveState(): void {
    try {
      fs.writeFileSync(
        path.join(this.config.dataDir, "checkpoints.json"),
        JSON.stringify(this.checkpoints.slice(-this.config.maxCheckpoints), null, 2)
      );

      const queuesData: Record<string, QueueItem[]> = {};
      for (const [key, value] of this.queues) {
        queuesData[key] = value;
      }
      fs.writeFileSync(
        path.join(this.config.dataDir, "queues.json"),
        JSON.stringify(queuesData, null, 2)
      );

      fs.writeFileSync(
        path.join(this.config.dataDir, "history.json"),
        JSON.stringify(this.history.slice(-this.config.maxHistory), null, 2)
      );

      fs.writeFileSync(
        path.join(this.config.dataDir, "version.json"),
        JSON.stringify({ version: this.stateVersion }, null, 2)
      );
    } catch (err) {
      console.error("[Persistence] Failed to save state:", err);
    }
  }

  private computeChecksum(data: unknown): string {
    return crypto
      .createHash("sha256")
      .update(JSON.stringify(data))
      .digest("hex")
      .slice(0, 16);
  }

  private generateId(): string {
    return `cp-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  // ── Checkpoints ────────────────────────────────────────────────────────

  /**
   * Save a checkpoint.
   */
  saveCheckpoint(
    type: Checkpoint["type"],
    entityId: string,
    state: unknown
  ): Checkpoint {
    const checkpoint: Checkpoint = {
      id: this.generateId(),
      timestamp: Date.now(),
      type,
      entityId,
      state,
      checksum: this.computeChecksum(state),
      version: this.stateVersion,
    };

    this.checkpoints.push(checkpoint);

    // Prune old checkpoints
    if (this.checkpoints.length > this.config.maxCheckpoints) {
      this.checkpoints = this.checkpoints.slice(-this.config.maxCheckpoints);
    }

    this.saveState();
    this.emit("checkpoint-saved", checkpoint);
    return checkpoint;
  }

  /**
   * Load the latest checkpoint for an entity.
   */
  loadCheckpoint(entityId: string): Checkpoint | null {
    const matching = this.checkpoints
      .filter((c) => c.entityId === entityId)
      .sort((a, b) => b.timestamp - a.timestamp);
    return matching[0] || null;
  }

  /**
   * Load all checkpoints for a type.
   */
  loadCheckpointsByType(type: Checkpoint["type"]): Checkpoint[] {
    return this.checkpoints
      .filter((c) => c.type === type)
      .sort((a, b) => b.timestamp - a.timestamp);
  }

  /**
   * Verify checkpoint integrity.
   */
  verifyCheckpoint(checkpointId: string): boolean {
    const checkpoint = this.checkpoints.find((c) => c.id === checkpointId);
    if (!checkpoint) return false;
    return checkpoint.checksum === this.computeChecksum(checkpoint.state);
  }

  /**
   * Get all checkpoints.
   */
  getCheckpoints(): Checkpoint[] {
    return [...this.checkpoints];
  }

  // ── Durable Queues ─────────────────────────────────────────────────────

  /**
   * Create or get a queue.
   */
  getQueue(queueName: string): QueueItem[] {
    if (!this.queues.has(queueName)) {
      this.queues.set(queueName, []);
    }
    return this.queues.get(queueName)!;
  }

  /**
   * Enqueue an item.
   */
  enqueue<T>(queueName: string, payload: T, priority: number = 0, maxRetries: number = 3): QueueItem<T> {
    const queue = this.getQueue(queueName);

    const item: QueueItem<T> = {
      id: `q-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      queue: queueName,
      payload,
      priority,
      enqueuedAt: Date.now(),
      status: "pending",
      retryCount: 0,
      maxRetries,
    };

    queue.push(item);
    // Sort by priority (higher = first)
    queue.sort((a, b) => b.priority - a.priority);

    this.saveState();
    this.emit("item-enqueued", item);
    return item;
  }

  /**
   * Dequeue the next item.
   */
  dequeue<T = unknown>(queueName: string): QueueItem<T> | null {
    const queue = this.getQueue(queueName);
    const item = queue.find((i) => i.status === "pending");
    if (!item) return null;

    item.status = "processing";
    item.dequeuedAt = Date.now();
    this.saveState();
    this.emit("item-dequeued", item);
    return item as QueueItem<T>;
  }

  /**
   * Complete a queue item.
   */
  completeQueueItem(queueName: string, itemId: string): boolean {
    const queue = this.getQueue(queueName);
    const item = queue.find((i) => i.id === itemId);
    if (!item) return false;

    item.status = "completed";
    this.saveState();
    this.emit("item-completed", item);
    return true;
  }

  /**
   * Fail a queue item.
   */
  failQueueItem(queueName: string, itemId: string, error: string): boolean {
    const queue = this.getQueue(queueName);
    const item = queue.find((i) => i.id === itemId);
    if (!item) return false;

    item.retryCount++;
    item.error = error;

    if (item.retryCount < item.maxRetries) {
      item.status = "pending";
      item.dequeuedAt = undefined;
    } else {
      item.status = "failed";
    }

    this.saveState();
    this.emit("item-failed", item);
    return true;
  }

  /**
   * Get queue stats.
   */
  getQueueStats(queueName: string): {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
    total: number;
  } {
    const queue = this.getQueue(queueName);
    return {
      pending: queue.filter((i) => i.status === "pending").length,
      processing: queue.filter((i) => i.status === "processing").length,
      completed: queue.filter((i) => i.status === "completed").length,
      failed: queue.filter((i) => i.status === "failed").length,
      total: queue.length,
    };
  }

  /**
   * Get all queue names.
   */
  getQueueNames(): string[] {
    return Array.from(this.queues.keys());
  }

  /**
   * Clear a queue.
   */
  clearQueue(queueName: string): void {
    this.queues.set(queueName, []);
    this.saveState();
    this.emit("queue-cleared", queueName);
  }

  // ── Execution History ──────────────────────────────────────────────────

  /**
   * Record a history entry.
   */
  recordHistory(
    entityType: HistoryEntry["entityType"],
    entityId: string,
    action: string,
    snapshot: unknown
  ): HistoryEntry {
    const entry: HistoryEntry = {
      id: `hist-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      entityType,
      entityId,
      action,
      timestamp: Date.now(),
      snapshot,
    };

    this.history.push(entry);

    if (this.history.length > this.config.maxHistory) {
      this.history = this.history.slice(-this.config.maxHistory);
    }

    this.saveState();
    this.emit("history-recorded", entry);
    return entry;
  }

  /**
   * Get history for an entity.
   */
  getEntityHistory(entityId: string): HistoryEntry[] {
    return this.history
      .filter((h) => h.entityId === entityId)
      .sort((a, b) => b.timestamp - a.timestamp);
  }

  /**
   * Get recent history.
   */
  getRecentHistory(limit = 50): HistoryEntry[] {
    return this.history.slice(-limit).sort((a, b) => b.timestamp - a.timestamp);
  }

  // ── State Versioning ───────────────────────────────────────────────────

  /**
   * Get the current state version.
   */
  getStateVersion(): number {
    return this.stateVersion;
  }

  /**
   * Bump the state version.
   */
  bumpVersion(): number {
    this.stateVersion++;
    this.saveState();
    this.emit("version-bumped", this.stateVersion);
    return this.stateVersion;
  }

  // ── Alias Methods (for IPC & Tests) ─────────────────────────────────────

  /**
   * Create a checkpoint (alias for saveCheckpoint with different signature).
   */
  createCheckpoint(checkpoint: Partial<Checkpoint>): Checkpoint {
    const cp: Checkpoint = {
      id: checkpoint.id || this.generateId(),
      timestamp: checkpoint.timestamp || Date.now(),
      type: checkpoint.type || "full",
      entityId: checkpoint.entityId || "",
      state: checkpoint.state || {},
      checksum: this.computeChecksum(checkpoint.state || {}),
      version: this.stateVersion,
    };
    this.checkpoints.push(cp);
    if (this.checkpoints.length > this.config.maxCheckpoints) {
      this.checkpoints = this.checkpoints.slice(-this.config.maxCheckpoints);
    }
    this.saveState();
    this.emit("checkpoint-saved", cp);
    return cp;
  }

  /**
   * Get a checkpoint by ID.
   */
  getCheckpoint(id: string): Checkpoint | null {
    return this.checkpoints.find((c) => c.id === id) || null;
  }

  /**
   * Restore a checkpoint by ID (returns the checkpoint state).
   */
  restoreCheckpoint(id: string): unknown | null {
    const cp = this.getCheckpoint(id);
    return cp ? cp.state : null;
  }

  /**
   * List checkpoints with optional goalId filter.
   */
  listCheckpoints(goalId?: string): Checkpoint[] {
    let result = [...this.checkpoints];
    if (goalId) {
      result = result.filter((c) => c.entityId === goalId);
    }
    return result.sort((a, b) => b.timestamp - a.timestamp);
  }

  /**
   * Peek at the next queue item without dequeuing.
   */
  peekQueue(queueName: string): QueueItem | null {
    const queue = this.getQueue(queueName);
    return queue.find((i) => i.status === "pending") || null;
  }

  /**
   * Get history with optional filters.
   */
  getHistory(filters?: { entityType?: string; entityId?: string; limit?: number }): HistoryEntry[] {
    let result = [...this.history];
    if (filters?.entityType) {
      result = result.filter((h) => h.entityType === filters.entityType);
    }
    if (filters?.entityId) {
      result = result.filter((h) => h.entityId === filters.entityId);
    }
    const limit = filters?.limit || 50;
    return result.slice(-limit).sort((a, b) => b.timestamp - a.timestamp);
  }

  /**
   * Export all state (alias for exportState).
   */
  exportAll(): string {
    return this.exportState();
  }

  /**
   * Import all state (alias for importState).
   */
  importAll(data: string): boolean {
    return this.importState(data);
  }

  /**
   * List state versions for a key.
   */
  listVersions(_key: string): number[] {
    return [this.stateVersion];
  }

  /**
   * Restore a specific version (bumps to that version).
   */
  restoreVersion(_key: string, version: number): boolean {
    if (version >= 1) {
      this.stateVersion = version;
      this.saveState();
      this.emit("version-restored", version);
      return true;
    }
    return false;
  }

  /**
   * Cleanup old data.
   */
  cleanup(maxHistory?: number): void {
    if (maxHistory && maxHistory > 0) {
      this.history = this.history.slice(-maxHistory);
    }
    // Remove failed queue items older than 24h
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    for (const [key, queue] of this.queues) {
      this.queues.set(
        key,
        queue.filter((i) => i.status !== "failed" || i.enqueuedAt > cutoff)
      );
    }
    this.saveState();
    this.emit("cleanup-completed");
  }

  /**
   * Get current state summary.
   */
  getState(): {
    checkpoints: number;
    queues: Record<string, number>;
    history: number;
    version: number;
  } {
    const queues: Record<string, number> = {};
    for (const [key, queue] of this.queues) {
      queues[key] = queue.length;
    }
    return {
      checkpoints: this.checkpoints.length,
      queues,
      history: this.history.length,
      version: this.stateVersion,
    };
  }

  // ── Auto-Checkpoint ────────────────────────────────────────────────────

  /**
   * Start auto-checkpointing.
   */
  startAutoCheckpoint(intervalMs?: number): void {
    if (this.checkpointTimer) return;
    this.checkpointTimer = setInterval(
      () => this.emit("auto-checkpoint"),
      intervalMs || this.config.checkpointInterval
    );
  }

  /**
   * Stop auto-checkpointing.
   */
  stopAutoCheckpoint(): void {
    if (this.checkpointTimer) {
      clearInterval(this.checkpointTimer);
      this.checkpointTimer = null;
    }
  }

  // ── Recovery ───────────────────────────────────────────────────────────

  /**
   * Get all entities that can be recovered.
   */
  getRecoverableEntities(): Checkpoint[] {
    // Get the latest checkpoint per entity
    const latest = new Map<string, Checkpoint>();
    for (const cp of this.checkpoints) {
      const existing = latest.get(cp.entityId);
      if (!existing || cp.timestamp > existing.timestamp) {
        latest.set(cp.entityId, cp);
      }
    }
    return Array.from(latest.values());
  }

  /**
   * Export all state for backup.
   */
  exportState(): string {
    return JSON.stringify({
      version: this.stateVersion,
      checkpoints: this.checkpoints,
      queues: Object.fromEntries(this.queues),
      history: this.history.slice(-1000),
      exportedAt: Date.now(),
    });
  }

  /**
   * Import state from backup.
   */
  importState(data: string): boolean {
    try {
      const parsed = JSON.parse(data);
      if (parsed.version) this.stateVersion = parsed.version;
      if (parsed.checkpoints) this.checkpoints = parsed.checkpoints;
      if (parsed.queues) {
        for (const [key, value] of Object.entries(parsed.queues)) {
          this.queues.set(key, value as QueueItem[]);
        }
      }
      if (parsed.history) this.history = parsed.history;
      this.saveState();
      this.emit("state-imported");
      return true;
    } catch {
      return false;
    }
  }

  // ── Cleanup ────────────────────────────────────────────────────────────

  /**
   * Clear all persistence data.
   */
  clearAll(): void {
    this.checkpoints = [];
    this.queues.clear();
    this.history = [];
    this.stateVersion = 1;
    this.saveState();
    this.emit("persistence-cleared");
  }

  /**
   * Destroy the persistence module.
   */
  destroy(): void {
    this.stopAutoCheckpoint();
    this.saveState();
  }
}

export default Persistence;
