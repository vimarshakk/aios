/**
 * Planner — DAG-based task decomposition and execution planning.
 *
 * Provides:
 * - Goal decomposition into executable task DAGs
 * - Dependency resolution with topological sort
 * - Progress tracking across the DAG
 * - Replanning when failures occur
 * - Critical path calculation
 */

import { EventEmitter } from "events";
import * as fs from "fs";
import * as path from "path";
import { app } from "electron";

export type TaskStatus =
  | "pending"
  | "ready"
  | "running"
  | "completed"
  | "failed"
  | "skipped"
  | "blocked";

export interface Task {
  id: string;
  name: string;
  description: string;
  status: TaskStatus;
  progress: number;
  agentId?: string;
  dependencies: string[];
  dependents: string[]; // tasks that depend on this
  estimatedDuration?: number; // ms
  actualDuration?: number;
  startedAt?: number;
  completedAt?: number;
  error?: string;
  retryCount: number;
  maxRetries: number;
  result?: unknown;
  metadata: Record<string, unknown>;
}

export interface Plan {
  id: string;
  goalId: string;
  name: string;
  description: string;
  tasks: Task[];
  status: "draft" | "active" | "completed" | "failed" | "replanning";
  progress: number;
  criticalPath: string[];
  createdAt: number;
  updatedAt: number;
  version: number;
}

export interface DependencyEdge {
  from: string;
  to: string;
}

export interface TopoSortResult {
  sorted: string[];
  cyclic: boolean;
  cycle?: string[];
}

export class Planner extends EventEmitter {
  private plans: Map<string, Plan> = new Map();
  private dataDir: string;

  constructor() {
    super();
    this.dataDir = path.join(app.getPath("userData"), "planner");
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
      const plansPath = path.join(this.dataDir, "plans.json");
      if (fs.existsSync(plansPath)) {
        const data = JSON.parse(fs.readFileSync(plansPath, "utf-8"));
        for (const plan of data) {
          this.plans.set(plan.id, plan);
        }
      }
    } catch { /* ignore */ }
  }

  private saveState(): void {
    try {
      const plansPath = path.join(this.dataDir, "plans.json");
      const plans = Array.from(this.plans.values());
      fs.writeFileSync(plansPath, JSON.stringify(plans, null, 2));
    } catch (err) {
      console.error("[Planner] Failed to save state:", err);
    }
  }

  private generateId(): string {
    return `plan-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  private generateTaskId(): string {
    return `task-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  /**
   * Create a new plan for a goal.
   */
  createPlan(goalId: string, name: string, description: string = ""): Plan {
    const plan: Plan = {
      id: this.generateId(),
      goalId,
      name,
      description,
      tasks: [],
      status: "draft",
      progress: 0,
      criticalPath: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
      version: 1,
    };

    this.plans.set(plan.id, plan);
    this.saveState();
    this.emit("plan-created", plan);
    return plan;
  }

  /**
   * Add a task to a plan.
   */
  addTask(
    planId: string,
    name: string,
    description: string = "",
    dependencies: string[] = [],
    options?: {
      agentId?: string;
      estimatedDuration?: number;
      maxRetries?: number;
      metadata?: Record<string, unknown>;
    }
  ): Task | null {
    const plan = this.plans.get(planId);
    if (!plan) return null;

    const task: Task = {
      id: this.generateTaskId(),
      name,
      description,
      status: "pending",
      progress: 0,
      dependencies,
      dependents: [],
      estimatedDuration: options?.estimatedDuration,
      retryCount: 0,
      maxRetries: options?.maxRetries ?? 3,
      agentId: options?.agentId,
      metadata: options?.metadata ?? {},
    };

    // Update dependents in existing tasks
    for (const depId of dependencies) {
      const depTask = plan.tasks.find((t) => t.id === depId);
      if (depTask) {
        depTask.dependents.push(task.id);
      }
    }

    plan.tasks.push(task);
    plan.updatedAt = Date.now();
    this.saveState();
    this.emit("task-added", { planId, task });
    return task;
  }

  /**
   * Topological sort of tasks.
   */
  topologicalSort(tasks: Task[]): TopoSortResult {
    const taskMap = new Map<string, Task>();
    for (const task of tasks) {
      taskMap.set(task.id, task);
    }

    const visited = new Set<string>();
    const visiting = new Set<string>();
    const sorted: string[] = [];
    const cycle: string[] = [];

    const dfs = (taskId: string): boolean => {
      if (visiting.has(taskId)) {
        cycle.push(taskId);
        return true; // cycle detected
      }
      if (visited.has(taskId)) return false;

      visiting.add(taskId);
      const task = taskMap.get(taskId);
      if (task) {
        for (const dep of task.dependencies) {
          if (dfs(dep)) {
            cycle.push(taskId);
            return true;
          }
        }
      }
      visiting.delete(taskId);
      visited.add(taskId);
      sorted.push(taskId);
      return false;
    };

    for (const task of tasks) {
      if (!visited.has(task.id)) {
        if (dfs(task.id)) {
          return { sorted: [], cyclic: true, cycle };
        }
      }
    }

    return { sorted, cyclic: false };
  }

  /**
   * Get dependency edges for a plan.
   */
  getDependencyEdges(planId: string): DependencyEdge[] {
    const plan = this.plans.get(planId);
    if (!plan) return [];

    const edges: DependencyEdge[] = [];
    for (const task of plan.tasks) {
      for (const dep of task.dependencies) {
        edges.push({ from: dep, to: task.id });
      }
    }
    return edges;
  }

  /**
   * Calculate the critical path (longest path through the DAG).
   */
  calculateCriticalPath(planId: string): string[] {
    const plan = this.plans.get(planId);
    if (!plan) return [];

    const result = this.topologicalSort(plan.tasks);
    if (result.cyclic || result.sorted.length === 0) return [];

    // Calculate longest path to each node
    const dist = new Map<string, number>();
    const prev = new Map<string, string | null>();

    for (const taskId of result.sorted) {
      dist.set(taskId, 0);
      prev.set(taskId, null);
    }

    for (const taskId of result.sorted) {
      const task = plan.tasks.find((t) => t.id === taskId);
      if (!task) continue;
      const taskDuration = task.estimatedDuration || 0;

      for (const dependentId of task.dependents) {
        const currentDist = dist.get(dependentId) || 0;
        const newDist = (dist.get(taskId) || 0) + taskDuration;
        if (newDist > currentDist) {
          dist.set(dependentId, newDist);
          prev.set(dependentId, taskId);
        }
      }
    }

    // Find the node with the longest distance
    let maxDist = 0;
    let endNode = "";
    for (const [taskId, d] of dist) {
      if (d > maxDist) {
        maxDist = d;
        endNode = taskId;
      }
    }

    // Reconstruct path
    const path: string[] = [];
    let current: string | null = endNode;
    while (current) {
      path.unshift(current);
      current = prev.get(current) ?? null;
    }

    return path;
  }

  /**
   * Activate a plan.
   */
  activatePlan(planId: string): boolean {
    const plan = this.plans.get(planId);
    if (!plan || plan.status !== "draft") return false;

    plan.status = "active";
    plan.criticalPath = this.calculateCriticalPath(planId);

    // Mark tasks with no dependencies as ready
    for (const task of plan.tasks) {
      if (task.dependencies.length === 0) {
        task.status = "ready";
      }
    }

    plan.updatedAt = Date.now();
    this.saveState();
    this.emit("plan-activated", plan);
    return true;
  }

  /**
   * Get the next executable task.
   */
  getNextTask(planId: string): Task | null {
    const plan = this.plans.get(planId);
    if (!plan || plan.status !== "active") return null;

    for (const task of plan.tasks) {
      if (task.status !== "ready") continue;

      // Verify all dependencies are completed
      const depsComplete = task.dependencies.every((depId) => {
        const dep = plan.tasks.find((t) => t.id === depId);
        return dep?.status === "completed" || dep?.status === "skipped";
      });

      if (depsComplete) return task;
    }

    return null;
  }

  /**
   * Start executing a task.
   */
  startTask(planId: string, taskId: string): boolean {
    const plan = this.plans.get(planId);
    if (!plan) return false;

    const task = plan.tasks.find((t) => t.id === taskId);
    if (!task || task.status !== "ready") return false;

    task.status = "running";
    task.startedAt = Date.now();
    plan.updatedAt = Date.now();
    this.saveState();
    this.emit("task-started", { planId, task });
    return true;
  }

  /**
   * Complete a task.
   */
  completeTask(planId: string, taskId: string, result?: unknown): boolean {
    const plan = this.plans.get(planId);
    if (!plan) return false;

    const task = plan.tasks.find((t) => t.id === taskId);
    if (!task || task.status !== "running") return false;

    task.status = "completed";
    task.progress = 100;
    task.completedAt = Date.now();
    task.result = result;
    if (task.startedAt) {
      task.actualDuration = task.completedAt - task.startedAt;
    }

    // Unblock dependent tasks
    for (const depId of task.dependents) {
      const dep = plan.tasks.find((t) => t.id === depId);
      if (!dep) continue;

      const allDepsMet = dep.dependencies.every((d) => {
        const dt = plan.tasks.find((t) => t.id === d);
        return dt?.status === "completed" || dt?.status === "skipped";
      });

      if (allDepsMet && dep.status === "pending") {
        dep.status = "ready";
      }
    }

    // Update plan progress
    this.updatePlanProgress(planId);

    plan.updatedAt = Date.now();
    this.saveState();
    this.emit("task-completed", { planId, task });
    return true;
  }

  /**
   * Fail a task and handle replanning.
   */
  failTask(planId: string, taskId: string, error: string): boolean {
    const plan = this.plans.get(planId);
    if (!plan) return false;

    const task = plan.tasks.find((t) => t.id === taskId);
    if (!task) return false;

    task.retryCount++;
    task.error = error;

    if (task.retryCount < task.maxRetries) {
      task.status = "ready";
      this.emit("task-retrying", { planId, task, attempt: task.retryCount });
    } else {
      task.status = "failed";

      // Block all dependent tasks
      this.blockDependents(planId, taskId);

      // Check if plan should fail
      const hasCriticalFailure = plan.criticalPath.includes(taskId);
      if (hasCriticalFailure) {
        plan.status = "failed";
        this.emit("plan-failed", { plan, task, error });
      }

      this.emit("task-failed", { planId, task, error });
    }

    this.updatePlanProgress(planId);
    plan.updatedAt = Date.now();
    this.saveState();
    return true;
  }

  /**
   * Block all tasks dependent on a failed task.
   */
  private blockDependents(planId: string, taskId: string): void {
    const plan = this.plans.get(planId);
    if (!plan) return;

    const task = plan.tasks.find((t) => t.id === taskId);
    if (!task) return;

    for (const depId of task.dependents) {
      const dep = plan.tasks.find((t) => t.id === depId);
      if (dep && (dep.status === "pending" || dep.status === "ready")) {
        dep.status = "blocked";
        this.blockDependents(planId, depId);
      }
    }
  }

  /**
   * Update plan progress based on task completion.
   */
  private updatePlanProgress(planId: string): void {
    const plan = this.plans.get(planId);
    if (!plan || plan.tasks.length === 0) return;

    const completed = plan.tasks.filter((t) => t.status === "completed").length;
    plan.progress = Math.round((completed / plan.tasks.length) * 100);

    if (completed === plan.tasks.length) {
      plan.status = "completed";
      this.emit("plan-completed", plan);
    }
  }

  /**
   * Replan after failures — create a new version with remaining tasks.
   */
  replan(planId: string): Plan | null {
    const original = this.plans.get(planId);
    if (!original) return null;

    const remainingTasks = original.tasks.filter(
      (t) => t.status === "failed" || t.status === "blocked"
    );

    if (remainingTasks.length === 0) return null;

    // Create new plan version
    const newPlan: Plan = {
      ...original,
      id: this.generateId(),
      status: "draft",
      progress: 0,
      version: original.version + 1,
      tasks: remainingTasks.map((t) => ({
        ...t,
        status: "pending" as TaskStatus,
        progress: 0,
        retryCount: 0,
        error: undefined,
        startedAt: undefined,
        completedAt: undefined,
        actualDuration: undefined,
      })),
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    this.plans.set(newPlan.id, newPlan);
    original.status = "replanning";
    this.saveState();
    this.emit("plan-replanned", { original: original.id, newPlan });
    return newPlan;
  }

  /**
   * Get a plan by ID.
   */
  getPlan(planId: string): Plan | undefined {
    return this.plans.get(planId);
  }

  /**
   * Get all plans.
   */
  getAllPlans(): Plan[] {
    return Array.from(this.plans.values());
  }

  /**
   * Get plan for a goal.
   */
  getPlanForGoal(goalId: string): Plan | undefined {
    return this.getAllPlans().find((p) => p.goalId === goalId);
  }

  /**
   * Delete a plan.
   */
  deletePlan(planId: string): boolean {
    const plan = this.plans.get(planId);
    if (!plan) return false;
    this.plans.delete(planId);
    this.saveState();
    this.emit("plan-deleted", planId);
    return true;
  }

  /**
   * Clear all plans.
   */
  clearAll(): void {
    this.plans.clear();
    this.saveState();
    this.emit("plans-cleared");
  }

  /**
   * Destroy the planner.
   */
  destroy(): void {
    this.saveState();
  }
}

export default Planner;
