/**
 * AgentRuntime — Multi-agent execution engine with capability routing.
 *
 * Provides:
 * - Agent registration and lifecycle management
 * - Capability-based routing
 * - Parallel agent execution
 * - Shared context and memory
 * - Inter-agent communication
 */

import { EventEmitter } from "events";
import * as fs from "fs";
import * as path from "path";
import { app } from "electron";

export type AgentStatus = "idle" | "running" | "paused" | "error" | "stopped";

export interface AgentCapability {
  name: string;
  description: string;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
}

export interface AgentConfig {
  id: string;
  name: string;
  description: string;
  capabilities: AgentCapability[];
  maxConcurrent: number;
  timeout: number; // ms
  metadata: Record<string, unknown>;
}

export interface AgentInstance {
  config: AgentConfig;
  status: AgentStatus;
  currentTask?: string;
  startedAt?: number;
  completedTasks: number;
  failedTasks: number;
  lastActive: number;
}

export interface AgentTask {
  id: string;
  agentId: string;
  capability: string;
  input: unknown;
  output?: unknown;
  error?: string;
  status: "pending" | "running" | "completed" | "failed";
  startedAt?: number;
  completedAt?: number;
  timeout?: number;
}

export interface SharedContext {
  workspace: string;
  memory: Map<string, unknown>;
  artifacts: Map<string, unknown>;
  variables: Map<string, unknown>;
}

export interface RuntimeState {
  totalAgents: number;
  activeAgents: number;
  totalTasks: number;
  completedTasks: number;
  failedTasks: number;
  uptime: number;
}

export class AgentRuntime extends EventEmitter {
  private agents: Map<string, AgentInstance> = new Map();
  private taskQueue: AgentTask[] = [];
  private runningTasks: Map<string, AgentTask> = new Map();
  private sharedContext: SharedContext;
  private dataDir: string;
  private startTime: number;
  private taskIdCounter = 0;

  constructor(workspace: string = "default") {
    super();
    this.dataDir = path.join(app.getPath("userData"), "agent-runtime");
    this.ensureDataDir();
    this.startTime = Date.now();
    this.sharedContext = {
      workspace,
      memory: new Map(),
      artifacts: new Map(),
      variables: new Map(),
    };
    this.loadState();
  }

  private ensureDataDir(): void {
    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
    }
  }

  private loadState(): void {
    try {
      const agentsPath = path.join(this.dataDir, "agents.json");
      if (fs.existsSync(agentsPath)) {
        const data = JSON.parse(fs.readFileSync(agentsPath, "utf-8"));
        for (const agent of data) {
          agent.config.capabilities = agent.config.capabilities || [];
          this.agents.set(agent.config.id, agent);
        }
      }

      const contextPath = path.join(this.dataDir, "context.json");
      if (fs.existsSync(contextPath)) {
        const data = JSON.parse(fs.readFileSync(contextPath, "utf-8"));
        if (data.memory) {
          this.sharedContext.memory = new Map(Object.entries(data.memory));
        }
        if (data.variables) {
          this.sharedContext.variables = new Map(Object.entries(data.variables));
        }
      }
    } catch { /* ignore */ }
  }

  private saveState(): void {
    try {
      const agents = Array.from(this.agents.values());
      fs.writeFileSync(path.join(this.dataDir, "agents.json"), JSON.stringify(agents, null, 2));

      const context = {
        memory: Object.fromEntries(this.sharedContext.memory),
        variables: Object.fromEntries(this.sharedContext.variables),
        workspace: this.sharedContext.workspace,
      };
      fs.writeFileSync(path.join(this.dataDir, "context.json"), JSON.stringify(context, null, 2));
    } catch (err) {
      console.error("[AgentRuntime] Failed to save state:", err);
    }
  }

  /**
   * Register an agent.
   */
  registerAgent(config: AgentConfig): AgentInstance {
    const instance: AgentInstance = {
      config,
      status: "idle",
      completedTasks: 0,
      failedTasks: 0,
      lastActive: Date.now(),
    };

    this.agents.set(config.id, instance);
    this.saveState();
    this.emit("agent-registered", instance);
    return instance;
  }

  /**
   * Unregister an agent.
   */
  unregisterAgent(agentId: string): boolean {
    const agent = this.agents.get(agentId);
    if (!agent) return false;

    agent.status = "stopped";
    this.agents.delete(agentId);
    this.saveState();
    this.emit("agent-unregistered", agentId);
    return true;
  }

  /**
   * Get agents that have a specific capability.
   */
  getAgentsWithCapability(capability: string): AgentInstance[] {
    return Array.from(this.agents.values()).filter(
      (agent) =>
        agent.status !== "stopped" &&
        agent.config.capabilities.some((c) => c.name === capability)
    );
  }

  /**
   * Route a task to the best agent based on capability.
   */
  routeTask(capability: string, input: unknown): AgentTask | null {
    const candidates = this.getAgentsWithCapability(capability).filter((agent) => {
      const runningCount = Array.from(this.runningTasks.values()).filter(
        (t) => t.agentId === agent.config.id && t.status === "running"
      ).length;
      return runningCount < agent.config.maxConcurrent;
    });

    if (candidates.length === 0) return null;

    // Pick the least loaded agent
    candidates.sort((a, b) => a.completedTasks - b.completedTasks);
    const selected = candidates[0];

    const task: AgentTask = {
      id: `task-${Date.now()}-${++this.taskIdCounter}`,
      agentId: selected.config.id,
      capability,
      input,
      status: "pending",
    };

    this.taskQueue.push(task);
    this.emit("task-routed", task);
    return task;
  }

  /**
   * Execute a task on an agent.
   */
  async executeTask(taskId: string): Promise<AgentTask | null> {
    const taskIndex = this.taskQueue.findIndex((t) => t.id === taskId);
    if (taskIndex === -1) return null;

    const task = this.taskQueue.splice(taskIndex, 1)[0];
    const agent = this.agents.get(task.agentId);
    if (!agent) return null;

    task.status = "running";
    task.startedAt = Date.now();
    task.timeout = agent.config.timeout;

    agent.status = "running";
    agent.currentTask = task.id;
    agent.lastActive = Date.now();

    this.runningTasks.set(task.id, task);
    this.emit("task-started", task);

    // Simulate execution (in production, this would call the agent's handler)
    return task;
  }

  /**
   * Complete a task.
   */
  completeTask(taskId: string, output: unknown): boolean {
    const task = this.runningTasks.get(taskId);
    if (!task) return false;

    task.status = "completed";
    task.output = output;
    task.completedAt = Date.now();

    const agent = this.agents.get(task.agentId);
    if (agent) {
      agent.status = "idle";
      agent.currentTask = undefined;
      agent.completedTasks++;
      agent.lastActive = Date.now();
    }

    this.runningTasks.delete(taskId);
    this.saveState();
    this.emit("task-completed", task);
    return true;
  }

  /**
   * Fail a task.
   */
  failTask(taskId: string, error: string): boolean {
    const task = this.runningTasks.get(taskId);
    if (!task) return false;

    task.status = "failed";
    task.error = error;
    task.completedAt = Date.now();

    const agent = this.agents.get(task.agentId);
    if (agent) {
      agent.status = "error";
      agent.currentTask = undefined;
      agent.failedTasks++;
      agent.lastActive = Date.now();
    }

    this.runningTasks.delete(taskId);
    this.saveState();
    this.emit("task-failed", { task, error });
    return true;
  }

  /**
   * Send a message between agents.
   */
  sendMessage(fromAgentId: string, toAgentId: string, message: unknown): boolean {
    const from = this.agents.get(fromAgentId);
    const to = this.agents.get(toAgentId);
    if (!from || !to) return false;

    this.emit("agent-message", { from: fromAgentId, to: toAgentId, message });
    return true;
  }

  /**
   * Broadcast a message to all agents.
   */
  broadcast(fromAgentId: string, message: unknown): void {
    this.emit("agent-broadcast", { from: fromAgentId, message });
  }

  /**
   * Set a shared context variable.
   */
  setVariable(key: string, value: unknown): void {
    this.sharedContext.variables.set(key, value);
    this.saveState();
    this.emit("variable-set", { key, value });
  }

  /**
   * Get a shared context variable.
   */
  getVariable(key: string): unknown {
    return this.sharedContext.variables.get(key);
  }

  /**
   * Store a memory entry.
   */
  setMemory(key: string, value: unknown): void {
    this.sharedContext.memory.set(key, value);
    this.saveState();
  }

  /**
   * Get a memory entry.
   */
  getMemory(key: string): unknown {
    return this.sharedContext.memory.get(key);
  }

  /**
   * Store an artifact.
   */
  setArtifact(key: string, value: unknown): void {
    this.sharedContext.artifacts.set(key, value);
    this.saveState();
  }

  /**
   * Get an artifact.
   */
  getArtifact(key: string): unknown {
    return this.sharedContext.artifacts.get(key);
  }

  /**
   * Get all registered agents.
   */
  getAgents(): AgentInstance[] {
    return Array.from(this.agents.values());
  }

  /**
   * Get an agent by ID.
   */
  getAgent(agentId: string): AgentInstance | undefined {
    return this.agents.get(agentId);
  }

  /**
   * Get all tasks (queued + running).
   */
  getTasks(): AgentTask[] {
    return [...this.taskQueue, ...Array.from(this.runningTasks.values())];
  }

  /**
   * Get runtime state.
   */
  getState(): RuntimeState {
    const agents = Array.from(this.agents.values());
    const allTasks = this.getTasks();
    return {
      totalAgents: agents.length,
      activeAgents: agents.filter((a) => a.status === "running").length,
      totalTasks: allTasks.length,
      completedTasks: agents.reduce((sum, a) => sum + a.completedTasks, 0),
      failedTasks: agents.reduce((sum, a) => sum + a.failedTasks, 0),
      uptime: Date.now() - this.startTime,
    };
  }

  /**
   * Clear the task queue.
   */
  clearQueue(): void {
    this.taskQueue = [];
    this.emit("queue-cleared");
  }

  /**
   * Clear all agents and context.
   */
  clearAll(): void {
    this.agents.clear();
    this.taskQueue = [];
    this.runningTasks.clear();
    this.sharedContext.memory.clear();
    this.sharedContext.artifacts.clear();
    this.sharedContext.variables.clear();
    this.saveState();
    this.emit("runtime-cleared");
  }

  /**
   * Destroy the runtime.
   */
  destroy(): void {
    this.saveState();
  }
}

export default AgentRuntime;
