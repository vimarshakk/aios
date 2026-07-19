/**
 * Supervisor — Persistent goal manager with priority scheduling.
 *
 * Provides:
 * - Goal lifecycle (create, plan, execute, complete, fail)
 * - Priority scheduling (critical, high, medium, low)
 * - Retry/recovery with configurable backoff
 * - Pause/resume/cancel support
 * - Long-running task management
 * - Event-driven state transitions
 */

import { EventEmitter } from "events";
import * as fs from "fs";
import * as path from "path";
import { app } from "electron";

export type GoalPriority = "critical" | "high" | "medium" | "low";

export type GoalStatus =
  | "created"
  | "planning"
  | "ready"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled";

export interface GoalStep {
  id: string;
  name: string;
  status: GoalStatus;
  progress: number; // 0-100
  startedAt?: number;
  completedAt?: number;
  error?: string;
  retryCount: number;
  maxRetries: number;
  agentId?: string;
  dependencies: string[]; // step IDs
  result?: unknown;
}

export interface Goal {
  id: string;
  title: string;
  description: string;
  priority: GoalPriority;
  status: GoalStatus;
  progress: number; // 0-100
  steps: GoalStep[];
  createdAt: number;
  updatedAt: number;
  startedAt?: number;
  completedAt?: number;
  pausedAt?: number;
  error?: string;
  tags: string[];
  metadata: Record<string, unknown>;
  parentId?: string;
  childIds: string[];
}

export interface SupervisorState {
  activeGoals: number;
  completedGoals: number;
  failedGoals: number;
  pausedGoals: number;
  totalGoals: number;
  uptime: number;
}

export interface RetryPolicy {
  maxRetries: number;
  backoffMs: number;
  backoffMultiplier: number;
  maxBackoffMs: number;
}

export class Supervisor extends EventEmitter {
  private goals: Map<string, Goal> = new Map();
  private queue: string[] = [];
  private running: Map<string, Goal> = new Map();
  private retryPolicy: RetryPolicy;
  private maxConcurrent: number;
  private dataDir: string;
  private startTime: number;
  private tickTimer: ReturnType<typeof setInterval> | null = null;

  constructor(config?: { retryPolicy?: Partial<RetryPolicy>; maxConcurrent?: number }) {
    super();
    this.dataDir = path.join(app.getPath("userData"), "supervisor");
    this.ensureDataDir();
    this.startTime = Date.now();

    this.retryPolicy = {
      maxRetries: 3,
      backoffMs: 1000,
      backoffMultiplier: 2,
      maxBackoffMs: 30000,
      ...config?.retryPolicy,
    };

    this.maxConcurrent = config?.maxConcurrent ?? 5;
    this.loadState();
  }

  private ensureDataDir(): void {
    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
    }
  }

  private loadState(): void {
    try {
      const goalsPath = path.join(this.dataDir, "goals.json");
      if (fs.existsSync(goalsPath)) {
        const data = JSON.parse(fs.readFileSync(goalsPath, "utf-8"));
        for (const goal of data) {
          this.goals.set(goal.id, goal);
        }
      }
    } catch { /* ignore */ }
  }

  private saveState(): void {
    try {
      const goalsPath = path.join(this.dataDir, "goals.json");
      const goals = Array.from(this.goals.values());
      fs.writeFileSync(goalsPath, JSON.stringify(goals, null, 2));
    } catch (err) {
      console.error("[Supervisor] Failed to save state:", err);
    }
  }

  private generateId(): string {
    return `goal-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  private generateStepId(): string {
    return `step-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  /**
   * Create a new goal.
   */
  createGoal(
    title: string,
    description: string,
    priority: GoalPriority = "medium",
    tags: string[] = [],
    metadata: Record<string, unknown> = {},
    parentId?: string
  ): Goal {
    const goal: Goal = {
      id: this.generateId(),
      title,
      description,
      priority,
      status: "created",
      progress: 0,
      steps: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
      tags,
      metadata,
      childIds: [],
      parentId,
    };

    this.goals.set(goal.id, goal);

    if (parentId) {
      const parent = this.goals.get(parentId);
      if (parent) {
        parent.childIds.push(goal.id);
      }
    }

    this.saveState();
    this.emit("goal-created", goal);
    return goal;
  }

  /**
   * Add a step to a goal.
   */
  addStep(
    goalId: string,
    name: string,
    dependencies: string[] = [],
    maxRetries?: number
  ): GoalStep | null {
    const goal = this.goals.get(goalId);
    if (!goal) return null;

    const step: GoalStep = {
      id: this.generateStepId(),
      name,
      status: "created",
      progress: 0,
      retryCount: 0,
      maxRetries: maxRetries ?? this.retryPolicy.maxRetries,
      dependencies,
    };

    goal.steps.push(step);
    goal.status = "ready";
    goal.updatedAt = Date.now();
    this.saveState();
    this.emit("step-added", { goalId, step });
    return step;
  }

  /**
   * Start executing a goal.
   */
  async startGoal(goalId: string): Promise<boolean> {
    const goal = this.goals.get(goalId);
    if (!goal) return false;

    if (goal.status !== "ready" && goal.status !== "created" && goal.status !== "paused") {
      return false;
    }

    goal.status = "running";
    goal.startedAt = Date.now();
    goal.updatedAt = Date.now();

    this.running.set(goalId, goal);
    this.queue = this.queue.filter((id) => id !== goalId);
    this.saveState();
    this.emit("goal-started", goal);
    return true;
  }

  /**
   * Pause a running goal.
   */
  pauseGoal(goalId: string): boolean {
    const goal = this.goals.get(goalId);
    if (!goal || goal.status !== "running") return false;

    goal.status = "paused";
    goal.pausedAt = Date.now();
    goal.updatedAt = Date.now();

    this.running.delete(goalId);
    this.saveState();
    this.emit("goal-paused", goal);
    return true;
  }

  /**
   * Resume a paused goal.
   */
  async resumeGoal(goalId: string): Promise<boolean> {
    const goal = this.goals.get(goalId);
    if (!goal || goal.status !== "paused") return false;
    return this.startGoal(goalId);
  }

  /**
   * Cancel a goal.
   */
  cancelGoal(goalId: string): boolean {
    const goal = this.goals.get(goalId);
    if (!goal) return false;
    if (goal.status === "completed" || goal.status === "cancelled") return false;

    goal.status = "cancelled";
    goal.completedAt = Date.now();
    goal.updatedAt = Date.now();

    this.running.delete(goalId);
    this.queue = this.queue.filter((id) => id !== goalId);
    this.saveState();
    this.emit("goal-cancelled", goal);
    return true;
  }

  /**
   * Mark a step as completed.
   */
  completeStep(goalId: string, stepId: string, result?: unknown): boolean {
    const goal = this.goals.get(goalId);
    if (!goal) return false;

    const step = goal.steps.find((s) => s.id === stepId);
    if (!step) return false;

    step.status = "completed";
    step.progress = 100;
    step.completedAt = Date.now();
    step.result = result;

    // Update goal progress
    const completedSteps = goal.steps.filter((s) => s.status === "completed").length;
    goal.progress = Math.round((completedSteps / goal.steps.length) * 100);
    goal.updatedAt = Date.now();

    // Check if goal is complete
    if (completedSteps === goal.steps.length) {
      goal.status = "completed";
      goal.completedAt = Date.now();
      this.running.delete(goalId);
      this.emit("goal-completed", goal);
    }

    this.saveState();
    this.emit("step-completed", { goalId, step });
    return true;
  }

  /**
   * Mark a step as failed and handle retry.
   */
  failStep(goalId: string, stepId: string, error: string): boolean {
    const goal = this.goals.get(goalId);
    if (!goal) return false;

    const step = goal.steps.find((s) => s.id === stepId);
    if (!step) return false;

    step.retryCount++;
    step.error = error;

    if (step.retryCount < step.maxRetries) {
      // Will retry on next tick
      step.status = "created";
      this.emit("step-retrying", { goalId, step, attempt: step.retryCount });
    } else {
      step.status = "failed";
      goal.status = "failed";
      goal.error = error;
      goal.updatedAt = Date.now();
      this.running.delete(goalId);
      this.emit("goal-failed", { goal, step, error });
    }

    this.saveState();
    return true;
  }

  /**
   * Update step progress.
   */
  updateStepProgress(goalId: string, stepId: string, progress: number): boolean {
    const goal = this.goals.get(goalId);
    if (!goal) return false;

    const step = goal.steps.find((s) => s.id === stepId);
    if (!step) return false;

    step.progress = Math.min(100, Math.max(0, progress));

    // Update overall goal progress proportionally
    const totalProgress = goal.steps.reduce((sum, s) => sum + s.progress, 0);
    goal.progress = Math.round(totalProgress / goal.steps.length);
    goal.updatedAt = Date.now();

    this.saveState();
    this.emit("step-progress", { goalId, stepId, progress: step.progress });
    return true;
  }

  /**
   * Enqueue a goal for scheduling.
   */
  enqueueGoal(goalId: string): boolean {
    const goal = this.goals.get(goalId);
    if (!goal) return false;
    if (goal.status !== "ready") return false;
    if (this.queue.includes(goalId)) return false;

    this.queue.push(goalId);
    this.sortQueue();
    this.emit("goal-enqueued", goal);
    return true;
  }

  /**
   * Sort queue by priority.
   */
  private sortQueue(): void {
    const priorityOrder: Record<GoalPriority, number> = {
      critical: 0,
      high: 1,
      medium: 2,
      low: 3,
    };

    this.queue.sort((a, b) => {
      const goalA = this.goals.get(a);
      const goalB = this.goals.get(b);
      if (!goalA || !goalB) return 0;
      return priorityOrder[goalA.priority] - priorityOrder[goalB.priority];
    });
  }

  /**
   * Process the queue and start next goals.
   */
  async tick(): Promise<void> {
    while (this.running.size < this.maxConcurrent && this.queue.length > 0) {
      const goalId = this.queue.shift()!;
      await this.startGoal(goalId);
    }
  }

  /**
   * Start the supervisor tick loop.
   */
  startTicking(intervalMs: number = 5000): void {
    if (this.tickTimer) return;
    this.tickTimer = setInterval(() => this.tick(), intervalMs);
  }

  /**
   * Stop the supervisor tick loop.
   */
  stopTicking(): void {
    if (this.tickTimer) {
      clearInterval(this.tickTimer);
      this.tickTimer = null;
    }
  }

  /**
   * Get a goal by ID.
   */
  getGoal(goalId: string): Goal | undefined {
    return this.goals.get(goalId);
  }

  /**
   * Get all goals.
   */
  getAllGoals(): Goal[] {
    return Array.from(this.goals.values());
  }

  /**
   * Get goals by status.
   */
  getGoalsByStatus(status: GoalStatus): Goal[] {
    return this.getAllGoals().filter((g) => g.status === status);
  }

  /**
   * Get goals by priority.
   */
  getGoalsByPriority(priority: GoalPriority): Goal[] {
    return this.getAllGoals().filter((g) => g.priority === priority);
  }

  /**
   * Get the next ready step for a goal.
   */
  getNextReadyStep(goalId: string): GoalStep | null {
    const goal = this.goals.get(goalId);
    if (!goal) return null;

    for (const step of goal.steps) {
      if (step.status !== "created") continue;

      // Check if all dependencies are satisfied
      const depsSatisfied = step.dependencies.every((depId) => {
        const dep = goal.steps.find((s) => s.id === depId);
        return dep?.status === "completed";
      });

      if (depsSatisfied) {
        step.status = "running";
        step.startedAt = Date.now();
        this.saveState();
        return step;
      }
    }

    return null;
  }

  /**
   * Get supervisor state.
   */
  getState(): SupervisorState {
    const goals = this.getAllGoals();
    return {
      activeGoals: goals.filter((g) => g.status === "running").length,
      completedGoals: goals.filter((g) => g.status === "completed").length,
      failedGoals: goals.filter((g) => g.status === "failed").length,
      pausedGoals: goals.filter((g) => g.status === "paused").length,
      totalGoals: goals.length,
      uptime: Date.now() - this.startTime,
    };
  }

  /**
   * Delete a goal.
   */
  deleteGoal(goalId: string): boolean {
    const goal = this.goals.get(goalId);
    if (!goal) return false;

    this.cancelGoal(goalId);
    this.goals.delete(goalId);
    this.saveState();
    this.emit("goal-deleted", goalId);
    return true;
  }

  /**
   * Get execution history.
   */
  getHistory(limit = 50): Goal[] {
    return this.getAllGoals()
      .filter((g) => g.status === "completed" || g.status === "failed" || g.status === "cancelled")
      .sort((a, b) => (b.completedAt || 0) - (a.completedAt || 0))
      .slice(0, limit);
  }

  /**
   * Clear all goals.
   */
  clearAll(): void {
    this.goals.clear();
    this.queue = [];
    this.running.clear();
    this.saveState();
    this.emit("goals-cleared");
  }

  /**
   * Destroy the supervisor.
   */
  destroy(): void {
    this.stopTicking();
    this.saveState();
  }
}

export default Supervisor;
