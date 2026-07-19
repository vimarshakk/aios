/**
 * WorkforceManager — Worker lifecycle, capability registry, and status tracking.
 *
 * Manages a pool of AI coding workers (Claude Code, OpenCode, Gemini CLI, etc.),
 * each backed by a different model/tool. Provides:
 *
 * - Worker registration and discovery
 * - Capability-based task routing
 * - Status tracking (idle, running, paused, error, offline)
 * - Worker health monitoring
 * - Persistent state
 */

import { EventEmitter } from "events";
import * as fs from "fs";
import * as path from "path";
import { app } from "electron";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type WorkerStatus = "idle" | "running" | "paused" | "error" | "offline";

export type WorkerRole =
  | "architect"
  | "backend"
  | "frontend"
  | "qa"
  | "devops"
  | "researcher"
  | "designer"
  | "reviewer";

export interface WorkerCapability {
  name: string;
  description: string;
  proficiency: number; // 0–100
}

export interface WorkerTerminal {
  pid?: number;
  cols: number;
  rows: number;
  shell: string;
}

export interface Worker {
  id: string;
  name: string;
  role: WorkerRole;
  status: WorkerStatus;
  cli: string; // e.g. "claude-code", "opencode", "gemini-cli"
  model?: string;
  capabilities: WorkerCapability[];
  terminal: WorkerTerminal;
  tasksCompleted: number;
  tasksFailed: number;
  avgDurationMs: number;
  uptime: number;
  lastActive: number;
  startedAt: number;
  metadata: Record<string, unknown>;
}

export interface WorkerTaskAssignment {
  workerId: string;
  taskId: string;
  assignedAt: number;
  status: "assigned" | "running" | "completed" | "failed";
  output?: unknown;
  error?: string;
}

export interface WorkforceState {
  totalWorkers: number;
  activeWorkers: number;
  idleWorkers: number;
  errorWorkers: number;
  offlineWorkers: number;
  totalTasksAssigned: number;
  uptime: number;
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const DEFAULT_WORKERS: Omit<Worker, "id" | "startedAt" | "lastActive" | "tasksCompleted" | "tasksFailed" | "avgDurationMs" | "uptime">[] = [
  {
    name: "Architect",
    role: "architect",
    status: "idle",
    cli: "claude-code",
    model: "claude-4-sonnet",
    capabilities: [
      { name: "system-design", description: "Design system architecture", proficiency: 95 },
      { name: "api-design", description: "Design API contracts", proficiency: 90 },
      { name: "database-design", description: "Design data models", proficiency: 85 },
    ],
    terminal: { cols: 120, rows: 40, shell: "bash" },
    metadata: {},
  },
  {
    name: "Backend Dev",
    role: "backend",
    status: "idle",
    cli: "opencode",
    model: "gpt-5.2",
    capabilities: [
      { name: "typescript", description: "TypeScript development", proficiency: 95 },
      { name: "python", description: "Python development", proficiency: 90 },
      { name: "database", description: "Database operations", proficiency: 85 },
      { name: "api", description: "REST/GraphQL API development", proficiency: 90 },
    ],
    terminal: { cols: 120, rows: 40, shell: "bash" },
    metadata: {},
  },
  {
    name: "Frontend Dev",
    role: "frontend",
    status: "idle",
    cli: "claude-code",
    model: "claude-4-sonnet",
    capabilities: [
      { name: "react", description: "React/Next.js development", proficiency: 95 },
      { name: "css", description: "CSS/Tailwind styling", proficiency: 90 },
      { name: "ui-components", description: "UI component development", proficiency: 85 },
    ],
    terminal: { cols: 120, rows: 40, shell: "bash" },
    metadata: {},
  },
  {
    name: "QA Engineer",
    role: "qa",
    status: "idle",
    cli: "gemini-cli",
    model: "gemini-2.5-pro",
    capabilities: [
      { name: "testing", description: "Test writing and execution", proficiency: 90 },
      { name: "code-review", description: "Code quality review", proficiency: 85 },
      { name: "bug-detection", description: "Bug identification", proficiency: 88 },
    ],
    terminal: { cols: 120, rows: 40, shell: "bash" },
    metadata: {},
  },
  {
    name: "DevOps",
    role: "devops",
    status: "idle",
    cli: "codex-cli",
    model: "o3",
    capabilities: [
      { name: "docker", description: "Docker/container management", proficiency: 90 },
      { name: "ci-cd", description: "CI/CD pipeline management", proficiency: 85 },
      { name: "deployment", description: "Deployment automation", proficiency: 88 },
    ],
    terminal: { cols: 120, rows: 40, shell: "bash" },
    metadata: {},
  },
  {
    name: "Researcher",
    role: "researcher",
    status: "idle",
    cli: "gemini-cli",
    model: "gemini-2.5-pro",
    capabilities: [
      { name: "documentation", description: "Documentation research", proficiency: 92 },
      { name: "web-search", description: "Web-based research", proficiency: 90 },
      { name: "analysis", description: "Technical analysis", proficiency: 85 },
    ],
    terminal: { cols: 120, rows: 40, shell: "bash" },
    metadata: {},
  },
  {
    name: "Designer",
    role: "designer",
    status: "idle",
    cli: "claude-code",
    model: "claude-4-sonnet",
    capabilities: [
      { name: "ui-design", description: "UI/UX design", proficiency: 90 },
      { name: "css-animation", description: "CSS animations", proficiency: 85 },
      { name: "design-system", description: "Design system creation", proficiency: 88 },
    ],
    terminal: { cols: 120, rows: 40, shell: "bash" },
    metadata: {},
  },
  {
    name: "Reviewer",
    role: "reviewer",
    status: "idle",
    cli: "opencode",
    model: "gpt-5.2",
    capabilities: [
      { name: "code-review", description: "Comprehensive code review", proficiency: 95 },
      { name: "security-audit", description: "Security vulnerability review", proficiency: 88 },
      { name: "performance-review", description: "Performance analysis", proficiency: 85 },
    ],
    terminal: { cols: 120, rows: 40, shell: "bash" },
    metadata: {},
  },
];

// ---------------------------------------------------------------------------
// WorkforceManager
// ---------------------------------------------------------------------------

export class WorkforceManager extends EventEmitter {
  private workers: Map<string, Worker> = new Map();
  private assignments: WorkerTaskAssignment[] = [];
  private dataDir: string;
  private startTime: number;
  private healthTimer: ReturnType<typeof setInterval> | null = null;
  private idCounter = 0;

  constructor() {
    super();
    this.dataDir = path.join(app.getPath("userData"), "workforce");
    this.ensureDataDir();
    this.startTime = Date.now();
    this.loadState();
    this.registerDefaults();
  }

  // -- Lifecycle ------------------------------------------------------------

  private ensureDataDir(): void {
    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
    }
  }

  private loadState(): void {
    try {
      const workersPath = path.join(this.dataDir, "workers.json");
      if (fs.existsSync(workersPath)) {
        const data = JSON.parse(fs.readFileSync(workersPath, "utf-8"));
        for (const w of data) {
          this.workers.set(w.id, w);
        }
      }
      const assignmentsPath = path.join(this.dataDir, "assignments.json");
      if (fs.existsSync(assignmentsPath)) {
        this.assignments = JSON.parse(fs.readFileSync(assignmentsPath, "utf-8"));
      }
    } catch { /* ignore */ }
  }

  private saveState(): void {
    try {
      const workers = Array.from(this.workers.values());
      fs.writeFileSync(
        path.join(this.dataDir, "workers.json"),
        JSON.stringify(workers, null, 2)
      );
      fs.writeFileSync(
        path.join(this.dataDir, "assignments.json"),
        JSON.stringify(this.assignments, null, 2)
      );
    } catch (err) {
      console.error("[WorkforceManager] Failed to save state:", err);
    }
  }

  private generateId(): string {
    return `worker-${Date.now()}-${++this.idCounter}`;
  }

  private registerDefaults(): void {
    if (this.workers.size > 0) return;
    for (const def of DEFAULT_WORKERS) {
      const worker: Worker = {
        ...def,
        id: this.generateId(),
        startedAt: Date.now(),
        lastActive: Date.now(),
        tasksCompleted: 0,
        tasksFailed: 0,
        avgDurationMs: 0,
        uptime: 0,
      };
      this.workers.set(worker.id, worker);
    }
    this.saveState();
  }

  // -- Worker management ----------------------------------------------------

  registerWorker(
    name: string,
    role: WorkerRole,
    cli: string,
    capabilities: WorkerCapability[],
    options?: { model?: string; shell?: string; cols?: number; rows?: number; metadata?: Record<string, unknown> }
  ): Worker {
    const worker: Worker = {
      id: this.generateId(),
      name,
      role,
      status: "idle",
      cli,
      model: options?.model,
      capabilities,
      terminal: {
        cols: options?.cols ?? 120,
        rows: options?.rows ?? 40,
        shell: options?.shell ?? "bash",
      },
      tasksCompleted: 0,
      tasksFailed: 0,
      avgDurationMs: 0,
      uptime: 0,
      lastActive: Date.now(),
      startedAt: Date.now(),
      metadata: options?.metadata ?? {},
    };
    this.workers.set(worker.id, worker);
    this.saveState();
    this.emit("worker-registered", worker);
    return worker;
  }

  unregisterWorker(workerId: string): boolean {
    const worker = this.workers.get(workerId);
    if (!worker) return false;
    worker.status = "offline";
    this.workers.delete(workerId);
    this.saveState();
    this.emit("worker-unregistered", workerId);
    return true;
  }

  getWorker(workerId: string): Worker | undefined {
    return this.workers.get(workerId);
  }

  getAllWorkers(): Worker[] {
    return Array.from(this.workers.values());
  }

  getWorkersByRole(role: WorkerRole): Worker[] {
    return this.getAllWorkers().filter((w) => w.role === role);
  }

  getWorkersByStatus(status: WorkerStatus): Worker[] {
    return this.getAllWorkers().filter((w) => w.status === status);
  }

  getWorkersByCapability(capability: string): Worker[] {
    return this.getAllWorkers().filter((w) =>
      w.capabilities.some((c) => c.name === capability)
    );
  }

  // -- Status management ----------------------------------------------------

  setWorkerStatus(workerId: string, status: WorkerStatus): boolean {
    const worker = this.workers.get(workerId);
    if (!worker) return false;
    const prev = worker.status;
    worker.status = status;
    worker.lastActive = Date.now();
    this.saveState();
    this.emit("worker-status-changed", { workerId, from: prev, to: status });
    return true;
  }

  // -- Task routing ---------------------------------------------------------

  /**
   * Find the best worker for a given capability, considering load and proficiency.
   */
  routeToWorker(capability: string): Worker | null {
    const candidates = this.getWorkersByCapability(capability).filter(
      (w) => w.status === "idle" || w.status === "running"
    );

    if (candidates.length === 0) return null;

    // Sort by proficiency (desc), then by tasks completed (asc = least loaded)
    candidates.sort((a, b) => {
      const capA = a.capabilities.find((c) => c.name === capability)?.proficiency ?? 0;
      const capB = b.capabilities.find((c) => c.name === capability)?.proficiency ?? 0;
      if (capB !== capA) return capB - capA;
      return a.tasksCompleted - b.tasksCompleted;
    });

    return candidates[0];
  }

  /**
   * Assign a task to a specific worker.
   */
  assignTask(workerId: string, taskId: string): WorkerTaskAssignment | null {
    const worker = this.workers.get(workerId);
    if (!worker) return null;

    const assignment: WorkerTaskAssignment = {
      workerId,
      taskId,
      assignedAt: Date.now(),
      status: "assigned",
    };

    this.assignments.push(assignment);
    worker.status = "running";
    worker.lastActive = Date.now();
    this.saveState();
    this.emit("task-assigned", assignment);
    return assignment;
  }

  /**
   * Complete a task assignment.
   */
  completeTask(workerId: string, taskId: string, output?: unknown): boolean {
    const assignment = this.assignments.find(
      (a) => a.workerId === workerId && a.taskId === taskId && a.status !== "completed" && a.status !== "failed"
    );
    if (!assignment) return false;

    assignment.status = "completed";
    assignment.output = output;

    const worker = this.workers.get(workerId);
    if (worker) {
      worker.tasksCompleted++;
      const duration = Date.now() - assignment.assignedAt;
      worker.avgDurationMs = Math.round(
        (worker.avgDurationMs * (worker.tasksCompleted - 1) + duration) / worker.tasksCompleted
      );
      worker.status = "idle";
      worker.lastActive = Date.now();
    }

    this.saveState();
    this.emit("task-completed", { workerId, taskId, output });
    return true;
  }

  /**
   * Fail a task assignment.
   */
  failTask(workerId: string, taskId: string, error: string): boolean {
    const assignment = this.assignments.find(
      (a) => a.workerId === workerId && a.taskId === taskId && a.status !== "completed" && a.status !== "failed"
    );
    if (!assignment) return false;

    assignment.status = "failed";
    assignment.error = error;

    const worker = this.workers.get(workerId);
    if (worker) {
      worker.tasksFailed++;
      worker.status = "error";
      worker.lastActive = Date.now();
    }

    this.saveState();
    this.emit("task-failed", { workerId, taskId, error });
    return true;
  }

  /**
   * Get all task assignments.
   */
  getAssignments(): WorkerTaskAssignment[] {
    return [...this.assignments];
  }

  /**
   * Get assignments for a worker.
   */
  getWorkerAssignments(workerId: string): WorkerTaskAssignment[] {
    return this.assignments.filter((a) => a.workerId === workerId);
  }

  // -- Health monitoring ----------------------------------------------------

  startHealthCheck(intervalMs: number = 30000): void {
    if (this.healthTimer) return;
    this.healthTimer = setInterval(() => this.checkHealth(), intervalMs);
  }

  stopHealthCheck(): void {
    if (this.healthTimer) {
      clearInterval(this.healthTimer);
      this.healthTimer = null;
    }
  }

  private checkHealth(): void {
    const now = Date.now();
    for (const worker of this.workers.values()) {
      if (worker.status === "running" && now - worker.lastActive > 5 * 60 * 1000) {
        worker.status = "error";
        this.emit("worker-unhealthy", worker);
      }
      worker.uptime = now - worker.startedAt;
    }
    this.saveState();
    this.emit("health-check", this.getState());
  }

  // -- State ----------------------------------------------------------------

  getState(): WorkforceState {
    const workers = this.getAllWorkers();
    return {
      totalWorkers: workers.length,
      activeWorkers: workers.filter((w) => w.status === "running").length,
      idleWorkers: workers.filter((w) => w.status === "idle").length,
      errorWorkers: workers.filter((w) => w.status === "error").length,
      offlineWorkers: workers.filter((w) => w.status === "offline").length,
      totalTasksAssigned: this.assignments.length,
      uptime: Date.now() - this.startTime,
    };
  }

  /**
   * Reset all workers to idle.
   */
  resetAll(): void {
    for (const worker of this.workers.values()) {
      worker.status = "idle";
      worker.lastActive = Date.now();
    }
    this.saveState();
    this.emit("workforce-reset");
  }

  destroy(): void {
    this.stopHealthCheck();
    this.saveState();
  }
}

export default WorkforceManager;
