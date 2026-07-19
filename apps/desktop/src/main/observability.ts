/**
 * Observability — Execution monitoring, cost tracking, and performance metrics.
 *
 * Provides:
 * - Live execution graph (real-time task/goal status)
 * - Goal timeline (chronological events per goal)
 * - Cost tracking (API calls, compute, storage)
 * - Token tracking (LLM usage)
 * - Performance metrics (latency, throughput, error rate)
 * - Metrics export
 */

import { EventEmitter } from "events";
import * as fs from "fs";
import * as path from "path";
import { app } from "electron";

export interface ExecutionNode {
  id: string;
  type: "goal" | "task" | "agent" | "workflow";
  label: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  parentId?: string;
  children: string[];
  startedAt?: number;
  completedAt?: number;
  duration?: number;
  metadata: Record<string, unknown>;
}

export interface ExecutionEdge {
  from: string;
  to: string;
  type: "depends" | "triggers" | "child";
}

export interface ExecutionGraph {
  nodes: ExecutionNode[];
  edges: ExecutionEdge[];
}

export interface TimelineEvent {
  id: string;
  goalId: string;
  type: "created" | "started" | "step-completed" | "step-failed" | "paused" | "resumed" | "completed" | "failed" | "cancelled";
  message: string;
  timestamp: number;
  metadata: Record<string, unknown>;
}

export interface CostEntry {
  id: string;
  category: "api" | "compute" | "storage" | "llm" | "other";
  description: string;
  amount: number;
  currency: string;
  timestamp: number;
  goalId?: string;
  taskId?: string;
}

export interface TokenUsage {
  provider: string;
  model: string;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  cost: number;
  timestamp: number;
  goalId?: string;
}

export interface PerformanceMetrics {
  totalExecutions: number;
  successRate: number;
  avgDuration: number;
  p95Duration: number;
  p99Duration: number;
  totalCost: number;
  totalTokens: number;
  activeGoals: number;
  activeTasks: number;
  errorRate: number;
  throughputPerHour: number;
}

export class Observability extends EventEmitter {
  private nodes: Map<string, ExecutionNode> = new Map();
  private edges: ExecutionEdge[] = [];
  private timelines: Map<string, TimelineEvent[]> = new Map();
  private costs: CostEntry[] = [];
  private tokenUsage: TokenUsage[] = [];
  private dataDir: string;

  constructor() {
    super();
    this.dataDir = path.join(app.getPath("userData"), "observability");
    this.ensureDataDir();
    this.loadState();
  }

  private ensureDataDir(): void {
    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
    }
  }

  private loadState(): void {
    try {
      const nodesPath = path.join(this.dataDir, "nodes.json");
      if (fs.existsSync(nodesPath)) {
        const data = JSON.parse(fs.readFileSync(nodesPath, "utf-8"));
        for (const node of data) {
          this.nodes.set(node.id, node);
        }
      }

      const edgesPath = path.join(this.dataDir, "edges.json");
      if (fs.existsSync(edgesPath)) {
        this.edges = JSON.parse(fs.readFileSync(edgesPath, "utf-8"));
      }

      const timelinesPath = path.join(this.dataDir, "timelines.json");
      if (fs.existsSync(timelinesPath)) {
        const data = JSON.parse(fs.readFileSync(timelinesPath, "utf-8"));
        for (const [key, value] of Object.entries(data)) {
          this.timelines.set(key, value as TimelineEvent[]);
        }
      }

      const costsPath = path.join(this.dataDir, "costs.json");
      if (fs.existsSync(costsPath)) {
        this.costs = JSON.parse(fs.readFileSync(costsPath, "utf-8"));
      }

      const tokensPath = path.join(this.dataDir, "tokens.json");
      if (fs.existsSync(tokensPath)) {
        this.tokenUsage = JSON.parse(fs.readFileSync(tokensPath, "utf-8"));
      }
    } catch { /* ignore */ }
  }

  private saveState(): void {
    try {
      fs.writeFileSync(
        path.join(this.dataDir, "nodes.json"),
        JSON.stringify(Array.from(this.nodes.values()), null, 2)
      );
      fs.writeFileSync(
        path.join(this.dataDir, "edges.json"),
        JSON.stringify(this.edges, null, 2)
      );

      const timelinesData: Record<string, TimelineEvent[]> = {};
      for (const [key, value] of this.timelines) {
        timelinesData[key] = value;
      }
      fs.writeFileSync(
        path.join(this.dataDir, "timelines.json"),
        JSON.stringify(timelinesData, null, 2)
      );

      // Keep last 10000 cost entries
      fs.writeFileSync(
        path.join(this.dataDir, "costs.json"),
        JSON.stringify(this.costs.slice(-10000), null, 2)
      );

      // Keep last 10000 token entries
      fs.writeFileSync(
        path.join(this.dataDir, "tokens.json"),
        JSON.stringify(this.tokenUsage.slice(-10000), null, 2)
      );
    } catch (err) {
      console.error("[Observability] Failed to save state:", err);
    }
  }

  private generateId(): string {
    return `obs-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  // ── Execution Graph ────────────────────────────────────────────────────

  /**
   * Add a node to the execution graph.
   */
  addNode(
    type: ExecutionNode["type"],
    label: string,
    status: ExecutionNode["status"] = "pending",
    parentId?: string,
    metadata: Record<string, unknown> = {}
  ): ExecutionNode {
    const node: ExecutionNode = {
      id: this.generateId(),
      type,
      label,
      status,
      parentId,
      children: [],
      metadata,
    };

    this.nodes.set(node.id, node);

    if (parentId) {
      const parent = this.nodes.get(parentId);
      if (parent) {
        parent.children.push(node.id);
        this.edges.push({ from: parentId, to: node.id, type: "child" });
      }
    }

    this.saveState();
    this.emit("node-added", node);
    return node;
  }

  /**
   * Update a node's status.
   */
  updateNodeStatus(
    nodeId: string,
    status: ExecutionNode["status"],
    metadata?: Record<string, unknown>
  ): boolean {
    const node = this.nodes.get(nodeId);
    if (!node) return false;

    node.status = status;
    if (status === "running" && !node.startedAt) {
      node.startedAt = Date.now();
    }
    if (status === "completed" || status === "failed" || status === "cancelled") {
      node.completedAt = Date.now();
      if (node.startedAt) {
        node.duration = node.completedAt - node.startedAt;
      }
    }
    if (metadata) {
      Object.assign(node.metadata, metadata);
    }

    this.saveState();
    this.emit("node-updated", node);
    return true;
  }

  /**
   * Add an edge between nodes.
   */
  addEdge(fromId: string, toId: string, type: ExecutionEdge["type"] = "depends"): void {
    const existing = this.edges.find(
      (e) => e.from === fromId && e.to === toId && e.type === type
    );
    if (!existing) {
      this.edges.push({ from: fromId, to: toId, type });
      this.saveState();
    }
  }

  /**
   * Get the full execution graph.
   */
  getGraph(): ExecutionGraph {
    return {
      nodes: Array.from(this.nodes.values()),
      edges: [...this.edges],
    };
  }

  /**
   * Get nodes by status.
   */
  getNodesByStatus(status: ExecutionNode["status"]): ExecutionNode[] {
    return Array.from(this.nodes.values()).filter((n) => n.status === status);
  }

  /**
   * Get nodes by type.
   */
  getNodesByType(type: ExecutionNode["type"]): ExecutionNode[] {
    return Array.from(this.nodes.values()).filter((n) => n.type === type);
  }

  // ── Goal Timeline ──────────────────────────────────────────────────────

  /**
   * Add an event to a goal's timeline.
   */
  addTimelineEvent(
    goalId: string,
    type: TimelineEvent["type"],
    message: string,
    metadata: Record<string, unknown> = {}
  ): TimelineEvent {
    const event: TimelineEvent = {
      id: this.generateId(),
      goalId,
      type,
      message,
      timestamp: Date.now(),
      metadata,
    };

    const timeline = this.timelines.get(goalId) || [];
    timeline.push(event);
    this.timelines.set(goalId, timeline);

    this.saveState();
    this.emit("timeline-event", event);
    return event;
  }

  /**
   * Get a goal's timeline.
   */
  getTimeline(goalId: string): TimelineEvent[] {
    return this.timelines.get(goalId) || [];
  }

  /**
   * Get all timelines.
   */
  getAllTimelines(): Map<string, TimelineEvent[]> {
    return new Map(this.timelines);
  }

  // ── Cost Tracking ──────────────────────────────────────────────────────

  /**
   * Record a cost entry.
   */
  recordCost(
    category: CostEntry["category"],
    description: string,
    amount: number,
    currency: string = "USD",
    goalId?: string,
    taskId?: string
  ): CostEntry {
    const entry: CostEntry = {
      id: this.generateId(),
      category,
      description,
      amount,
      currency,
      timestamp: Date.now(),
      goalId,
      taskId,
    };

    this.costs.push(entry);
    this.saveState();
    this.emit("cost-recorded", entry);
    return entry;
  }

  /**
   * Get total cost by category.
   */
  getCostsByCategory(): Record<string, number> {
    const totals: Record<string, number> = {};
    for (const entry of this.costs) {
      totals[entry.category] = (totals[entry.category] || 0) + entry.amount;
    }
    return totals;
  }

  /**
   * Get total cost.
   */
  getTotalCost(): number {
    return this.costs.reduce((sum, e) => sum + e.amount, 0);
  }

  /**
   * Get cost entries.
   */
  getCosts(limit = 100): CostEntry[] {
    return this.costs.slice(-limit);
  }

  // ── Token Tracking ─────────────────────────────────────────────────────

  /**
   * Record token usage.
   */
  recordTokenUsage(
    provider: string,
    model: string,
    inputTokens: number,
    outputTokens: number,
    cost: number,
    goalId?: string
  ): TokenUsage {
    const usage: TokenUsage = {
      provider,
      model,
      inputTokens,
      outputTokens,
      totalTokens: inputTokens + outputTokens,
      cost,
      timestamp: Date.now(),
      goalId,
    };

    this.tokenUsage.push(usage);
    this.saveState();
    this.emit("tokens-recorded", usage);
    return usage;
  }

  /**
   * Get total token usage.
   */
  getTotalTokens(): number {
    return this.tokenUsage.reduce((sum, u) => sum + u.totalTokens, 0);
  }

  /**
   * Get token usage by provider.
   */
  getTokensByProvider(): Record<string, number> {
    const totals: Record<string, number> = {};
    for (const entry of this.tokenUsage) {
      totals[entry.provider] = (totals[entry.provider] || 0) + entry.totalTokens;
    }
    return totals;
  }

  /**
   * Get token usage entries.
   */
  getTokenUsage(limit = 100): TokenUsage[] {
    return this.tokenUsage.slice(-limit);
  }

  // ── Performance Metrics ────────────────────────────────────────────────

  /**
   * Calculate performance metrics.
   */
  getPerformanceMetrics(): PerformanceMetrics {
    const nodes = Array.from(this.nodes.values());
    const completedNodes = nodes.filter(
      (n) => n.status === "completed" || n.status === "failed"
    );
    const successfulNodes = nodes.filter((n) => n.status === "completed");
    const durations = completedNodes
      .map((n) => n.duration || 0)
      .filter((d) => d > 0)
      .sort((a, b) => a - b);

    const totalCost = this.getTotalCost();
    const totalTokens = this.getTotalTokens();

    const activeGoals = nodes.filter(
      (n) => n.type === "goal" && n.status === "running"
    ).length;
    const activeTasks = nodes.filter(
      (n) => n.type === "task" && n.status === "running"
    ).length;

    // Throughput: completed items per hour
    const oneHourAgo = Date.now() - 3600000;
    const recentCompleted = completedNodes.filter(
      (n) => (n.completedAt || 0) > oneHourAgo
    ).length;

    return {
      totalExecutions: completedNodes.length,
      successRate:
        completedNodes.length > 0
          ? Math.round((successfulNodes.length / completedNodes.length) * 100)
          : 0,
      avgDuration:
        durations.length > 0
          ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length)
          : 0,
      p95Duration: durations.length > 0 ? durations[Math.floor(durations.length * 0.95)] || 0 : 0,
      p99Duration: durations.length > 0 ? durations[Math.floor(durations.length * 0.99)] || 0 : 0,
      totalCost,
      totalTokens,
      activeGoals,
      activeTasks,
      errorRate:
        completedNodes.length > 0
          ? Math.round(
              ((completedNodes.length - successfulNodes.length) / completedNodes.length) * 100
            )
          : 0,
      throughputPerHour: recentCompleted,
    };
  }

  /**
   * Get a full snapshot.
   */
  getSnapshot(): {
    graph: ExecutionGraph;
    metrics: PerformanceMetrics;
    costByCategory: Record<string, number>;
    tokensByProvider: Record<string, number>;
    recentTimelines: Record<string, TimelineEvent[]>;
  } {
    const recentTimelines: Record<string, TimelineEvent[]> = {};
    for (const [goalId, events] of this.timelines) {
      recentTimelines[goalId] = events.slice(-10);
    }

    return {
      graph: this.getGraph(),
      metrics: this.getPerformanceMetrics(),
      costByCategory: this.getCostsByCategory(),
      tokensByProvider: this.getTokensByProvider(),
      recentTimelines,
    };
  }

  // ── Cleanup ────────────────────────────────────────────────────────────

  /**
   * Remove old nodes.
   */
  pruneOldNodes(maxAge: number = 86400000): number {
    const cutoff = Date.now() - maxAge;
    let pruned = 0;

    for (const [id, node] of this.nodes) {
      if (node.completedAt && node.completedAt < cutoff) {
        this.nodes.delete(id);
        pruned++;
      }
    }

    if (pruned > 0) {
      this.edges = this.edges.filter(
        (e) => this.nodes.has(e.from) && this.nodes.has(e.to)
      );
      this.saveState();
    }

    return pruned;
  }

  /**
   * Clear all observability data.
   */
  clearAll(): void {
    this.nodes.clear();
    this.edges = [];
    this.timelines.clear();
    this.costs = [];
    this.tokenUsage = [];
    this.saveState();
    this.emit("observability-cleared");
  }

  /**
   * Destroy the observability module.
   */
  destroy(): void {
    this.saveState();
  }
}

export default Observability;
