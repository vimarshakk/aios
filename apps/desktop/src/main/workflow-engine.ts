/**
 * WorkflowEngine — Event-driven workflow orchestration.
 *
 * Provides:
 * - Event triggers and handlers
 * - Scheduled jobs (cron-like)
 * - Conditional workflows (if/else, loops)
 * - Background execution
 * - Workflow state machine
 */

import { EventEmitter } from "events";
import * as fs from "fs";
import * as path from "path";
import { app } from "electron";

export type WorkflowStatus = "idle" | "running" | "paused" | "completed" | "failed";

export type StepType = "action" | "condition" | "delay" | "parallel" | "loop";

export interface WorkflowStep {
  id: string;
  name: string;
  type: StepType;
  action?: string;
  condition?: string;
  delayMs?: number;
  children?: string[]; // for parallel/loop
  next?: string;
  onError?: "stop" | "skip" | "retry" | "goto";
  onErrorTarget?: string;
  maxRetries: number;
  retryCount: number;
  timeout: number; // ms
  metadata: Record<string, unknown>;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  steps: WorkflowStep[];
  status: WorkflowStatus;
  currentStepId?: string;
  context: Record<string, unknown>;
  createdAt: number;
  updatedAt: number;
  startedAt?: number;
  completedAt?: number;
  error?: string;
  runCount: number;
  enabled: boolean;
}

export interface WorkflowTrigger {
  id: string;
  workflowId: string;
  type: "event" | "schedule" | "manual";
  eventName?: string;
  cron?: string;
  enabled: boolean;
}

export interface WorkflowEvent {
  type: string;
  payload: unknown;
  timestamp: number;
  source: string;
}

export interface ScheduledJob {
  id: string;
  workflowId: string;
  intervalMs: number;
  lastRun?: number;
  nextRun: number;
  enabled: boolean;
}

export class WorkflowEngine extends EventEmitter {
  private workflows: Map<string, Workflow> = new Map();
  private triggers: Map<string, WorkflowTrigger> = new Map();
  private scheduledJobs: Map<string, ScheduledJob> = new Map();
  private eventHistory: WorkflowEvent[] = [];
  private dataDir: string;
  private scheduleTimer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    super();
    this.dataDir = path.join(app.getPath("userData"), "workflows");
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
      const workflowsPath = path.join(this.dataDir, "workflows.json");
      if (fs.existsSync(workflowsPath)) {
        const data = JSON.parse(fs.readFileSync(workflowsPath, "utf-8"));
        for (const w of data) {
          this.workflows.set(w.id, w);
        }
      }

      const triggersPath = path.join(this.dataDir, "triggers.json");
      if (fs.existsSync(triggersPath)) {
        const data = JSON.parse(fs.readFileSync(triggersPath, "utf-8"));
        for (const t of data) {
          this.triggers.set(t.id, t);
        }
      }

      const jobsPath = path.join(this.dataDir, "jobs.json");
      if (fs.existsSync(jobsPath)) {
        const data = JSON.parse(fs.readFileSync(jobsPath, "utf-8"));
        for (const j of data) {
          this.scheduledJobs.set(j.id, j);
        }
      }
    } catch { /* ignore */ }
  }

  private saveState(): void {
    try {
      fs.writeFileSync(
        path.join(this.dataDir, "workflows.json"),
        JSON.stringify(Array.from(this.workflows.values()), null, 2)
      );
      fs.writeFileSync(
        path.join(this.dataDir, "triggers.json"),
        JSON.stringify(Array.from(this.triggers.values()), null, 2)
      );
      fs.writeFileSync(
        path.join(this.dataDir, "jobs.json"),
        JSON.stringify(Array.from(this.scheduledJobs.values()), null, 2)
      );
    } catch (err) {
      console.error("[WorkflowEngine] Failed to save state:", err);
    }
  }

  private generateId(): string {
    return `wf-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  /**
   * Create a workflow.
   */
  createWorkflow(
    name: string,
    description: string = "",
    steps: WorkflowStep[] = []
  ): Workflow {
    const workflow: Workflow = {
      id: this.generateId(),
      name,
      description,
      steps,
      status: "idle",
      context: {},
      createdAt: Date.now(),
      updatedAt: Date.now(),
      runCount: 0,
      enabled: true,
    };

    this.workflows.set(workflow.id, workflow);
    this.saveState();
    this.emit("workflow-created", workflow);
    return workflow;
  }

  /**
   * Add a step to a workflow.
   */
  addStep(
    workflowId: string,
    step: Omit<WorkflowStep, "id" | "retryCount" | "metadata"> & {
      metadata?: Record<string, unknown>;
    }
  ): WorkflowStep | null {
    const workflow = this.workflows.get(workflowId);
    if (!workflow) return null;

    const fullStep: WorkflowStep = {
      id: `step-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      retryCount: 0,
      metadata: {},
      ...step,
    };

    workflow.steps.push(fullStep);
    workflow.updatedAt = Date.now();
    this.saveState();
    this.emit("step-added", { workflowId, step: fullStep });
    return fullStep;
  }

  /**
   * Register an event trigger.
   */
  registerTrigger(
    workflowId: string,
    type: WorkflowTrigger["type"],
    options?: { eventName?: string; cron?: string }
  ): WorkflowTrigger | null {
    const workflow = this.workflows.get(workflowId);
    if (!workflow) return null;

    const trigger: WorkflowTrigger = {
      id: `trigger-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      workflowId,
      type,
      eventName: options?.eventName,
      cron: options?.cron,
      enabled: true,
    };

    this.triggers.set(trigger.id, trigger);
    this.saveState();
    this.emit("trigger-registered", trigger);
    return trigger;
  }

  /**
   * Schedule a recurring job.
   */
  scheduleJob(workflowId: string, intervalMs: number): ScheduledJob | null {
    const workflow = this.workflows.get(workflowId);
    if (!workflow) return null;

    const job: ScheduledJob = {
      id: `job-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      workflowId,
      intervalMs,
      nextRun: Date.now() + intervalMs,
      enabled: true,
    };

    this.scheduledJobs.set(job.id, job);
    this.saveState();
    this.emit("job-scheduled", job);
    return job;
  }

  /**
   * Start the scheduler loop.
   */
  startScheduler(intervalMs: number = 1000): void {
    if (this.scheduleTimer) return;
    this.scheduleTimer = setInterval(() => this.checkScheduledJobs(), intervalMs);
  }

  /**
   * Stop the scheduler loop.
   */
  stopScheduler(): void {
    if (this.scheduleTimer) {
      clearInterval(this.scheduleTimer);
      this.scheduleTimer = null;
    }
  }

  /**
   * Check and run scheduled jobs.
   */
  private checkScheduledJobs(): void {
    const now = Date.now();
    for (const job of this.scheduledJobs.values()) {
      if (!job.enabled) continue;
      if (now >= job.nextRun) {
        job.lastRun = now;
        job.nextRun = now + job.intervalMs;
        this.runWorkflow(job.workflowId);
      }
    }
  }

  /**
   * Fire an event and trigger matching workflows.
   */
  fireEvent(type: string, payload: unknown, source: string = "system"): void {
    const event: WorkflowEvent = { type, payload, timestamp: Date.now(), source };
    this.eventHistory.push(event);
    if (this.eventHistory.length > 1000) {
      this.eventHistory = this.eventHistory.slice(-1000);
    }

    // Find triggers matching this event
    for (const trigger of this.triggers.values()) {
      if (trigger.type === "event" && trigger.eventName === type && trigger.enabled) {
        this.runWorkflow(trigger.workflowId, { event });
      }
    }

    this.emit("event-fired", event);
  }

  /**
   * Run a workflow.
   */
  async runWorkflow(
    workflowId: string,
    initialContext: Record<string, unknown> = {}
  ): Promise<boolean> {
    const workflow = this.workflows.get(workflowId);
    if (!workflow || !workflow.enabled) return false;
    if (workflow.status === "running") return false;

    workflow.status = "running";
    workflow.startedAt = Date.now();
    workflow.runCount++;
    workflow.context = { ...workflow.context, ...initialContext };
    workflow.currentStepId = workflow.steps[0]?.id;

    this.saveState();
    this.emit("workflow-started", workflow);

    // Execute steps sequentially
    await this.executeStepChain(workflow);

    return true;
  }

  /**
   * Execute a chain of steps.
   */
  private async executeStepChain(workflow: Workflow): Promise<void> {
    let stepId = workflow.steps[0]?.id;

    while (stepId) {
      const step = workflow.steps.find((s) => s.id === stepId);
      if (!step) break;

      workflow.currentStepId = stepId;
      this.emit("step-executing", { workflowId: workflow.id, step });

      try {
        const nextStepId = await this.executeStep(workflow, step);

        if (workflow.status !== "running") break;

        stepId = nextStepId;
      } catch (err) {
        step.retryCount++;
        if (step.retryCount < step.maxRetries && step.onError === "retry") {
          this.emit("step-retrying", { workflowId: workflow.id, step });
          continue;
        }

        if (step.onError === "goto" && step.onErrorTarget) {
          stepId = step.onErrorTarget;
          continue;
        }

        if (step.onError === "skip") {
          stepId = step.next;
          continue;
        }

        // Default: stop
        workflow.status = "failed";
        workflow.error = String(err);
        workflow.completedAt = Date.now();
        this.saveState();
        this.emit("workflow-failed", { workflow, error: err });
        return;
      }
    }

    workflow.status = "completed";
    workflow.completedAt = Date.now();
    workflow.currentStepId = undefined;
    this.saveState();
    this.emit("workflow-completed", workflow);
  }

  /**
   * Execute a single step.
   */
  private async executeStep(workflow: Workflow, step: WorkflowStep): Promise<string | null> {
    switch (step.type) {
      case "action":
        this.emit("action-executing", { workflowId: workflow.id, step });
        // Simulate action execution
        await this.delay(10);
        return step.next;

      case "condition": {
        const result = this.evaluateCondition(step.condition || "", workflow.context);
        return result ? step.next : (step.onErrorTarget || null);
      }

      case "delay":
        await this.delay(step.delayMs || 1000);
        return step.next;

      case "parallel":
        // Execute children in parallel
        if (step.children) {
          await Promise.all(
            step.children.map((childId) => {
              const child = workflow.steps.find((s) => s.id === childId);
              if (child) return this.executeStep(workflow, child);
              return Promise.resolve(null);
            })
          );
        }
        return step.next;

      case "loop": {
        // Simple loop: execute children, then return to loop start
        if (step.children) {
          for (const childId of step.children) {
            const child = workflow.steps.find((s) => s.id === childId);
            if (child) await this.executeStep(workflow, child);
          }
        }
        return step.next;
      }

      default:
        return step.next;
    }
  }

  /**
   * Evaluate a condition string.
   */
  private evaluateCondition(condition: string, context: Record<string, unknown>): boolean {
    if (!condition) return true;
    // Simple key=value or key!=value evaluation
    const parts = condition.split(/[=!]+/);
    if (parts.length === 2) {
      const key = parts[0].trim();
      const value = parts[1].trim();
      const contextValue = String(context[key] ?? "");
      if (condition.includes("!=")) return contextValue !== value;
      return contextValue === value;
    }
    return Boolean(context[condition]);
  }

  /**
   * Pause a running workflow.
   */
  pauseWorkflow(workflowId: string): boolean {
    const workflow = this.workflows.get(workflowId);
    if (!workflow || workflow.status !== "running") return false;

    workflow.status = "paused";
    this.saveState();
    this.emit("workflow-paused", workflow);
    return true;
  }

  /**
   * Resume a paused workflow.
   */
  async resumeWorkflow(workflowId: string): Promise<boolean> {
    const workflow = this.workflows.get(workflowId);
    if (!workflow || workflow.status !== "paused") return false;

    workflow.status = "running";
    this.saveState();
    await this.executeStepChain(workflow);
    return true;
  }

  /**
   * Stop a workflow.
   */
  stopWorkflow(workflowId: string): boolean {
    const workflow = this.workflows.get(workflowId);
    if (!workflow) return false;

    workflow.status = "idle";
    workflow.currentStepId = undefined;
    this.saveState();
    this.emit("workflow-stopped", workflow);
    return true;
  }

  /**
   * Get a workflow.
   */
  getWorkflow(workflowId: string): Workflow | undefined {
    return this.workflows.get(workflowId);
  }

  /**
   * Get all workflows.
   */
  getAllWorkflows(): Workflow[] {
    return Array.from(this.workflows.values());
  }

  /**
   * Get all triggers.
   */
  getAllTriggers(): WorkflowTrigger[] {
    return Array.from(this.triggers.values());
  }

  /**
   * Get event history.
   */
  getEventHistory(limit = 100): WorkflowEvent[] {
    return this.eventHistory.slice(-limit);
  }

  /**
   * Delete a workflow.
   */
  deleteWorkflow(workflowId: string): boolean {
    const workflow = this.workflows.get(workflowId);
    if (!workflow) return false;

    this.stopWorkflow(workflowId);
    this.workflows.delete(workflowId);

    // Remove associated triggers and jobs
    for (const [id, trigger] of this.triggers) {
      if (trigger.workflowId === workflowId) this.triggers.delete(id);
    }
    for (const [id, job] of this.scheduledJobs) {
      if (job.workflowId === workflowId) this.scheduledJobs.delete(id);
    }

    this.saveState();
    this.emit("workflow-deleted", workflowId);
    return true;
  }

  /**
   * Clear all workflows.
   */
  clearAll(): void {
    this.workflows.clear();
    this.triggers.clear();
    this.scheduledJobs.clear();
    this.eventHistory = [];
    this.saveState();
    this.emit("workflows-cleared");
  }

  /**
   * Destroy the workflow engine.
   */
  destroy(): void {
    this.stopScheduler();
    this.saveState();
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

export default WorkflowEngine;
