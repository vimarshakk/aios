/**
 * CLIController — Spawn, monitor, and control external AI CLI processes.
 *
 * Each worker type (Claude Code, OpenCode, Gemini CLI, Codex CLI) is backed by
 * an adapter that knows how to launch, interrupt, detect completion, and collect
 * output from the specific CLI binary.
 *
 * Provides:
 * - Process lifecycle (spawn, stop, interrupt, restart)
 * - Output streaming (stdout/stderr → event)
 * - Completion detection (exit code + pattern matching)
 * - Adapter registry per CLI type
 */

import { EventEmitter } from "events";
import { spawn, ChildProcess } from "child_process";
import type { Worker } from "./workforce-manager";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CLIAdapter {
  /** CLI identifier (e.g. "claude-code") */
  name: string;
  /** Binary or command to execute */
  command: string;
  /** Default args for interactive mode */
  defaultArgs: string[];
  /** Build args for a task prompt */
  buildArgs(prompt: string, cwd?: string): string[];
  /** Environment variables */
  env?: Record<string, string>;
  /** How to detect completion in stdout */
  completionPattern?: RegExp;
  /** How to send interrupt (e.g. SIGINT, SIGTERM) */
  interruptSignal?: NodeJS.Signals;
}

export interface CLIProcess {
  workerId: string;
  cliName: string;
  pid?: number;
  process?: ChildProcess;
  status: "idle" | "spawning" | "running" | "completing" | "stopped" | "error";
  startedAt: number;
  lastOutput: number;
  stdout: string[];
  stderr: string[];
  exitCode?: number;
  error?: string;
}

export interface CLIControllerState {
  totalProcesses: number;
  activeProcesses: number;
  stoppedProcesses: number;
  errorProcesses: number;
}

// ---------------------------------------------------------------------------
// Built-in Adapters
// ---------------------------------------------------------------------------

const CLAUDE_CODE_ADAPTER: CLIAdapter = {
  name: "claude-code",
  command: "claude",
  defaultArgs: ["--print"],
  buildArgs(prompt, cwd) {
    const args = ["--print"];
    if (cwd) args.push("--cwd", cwd);
    args.push(prompt);
    return args;
  },
  interruptSignal: "SIGINT",
};

const OPENCODE_ADAPTER: CLIAdapter = {
  name: "opencode",
  command: "opencode",
  defaultArgs: ["run"],
  buildArgs(prompt, cwd) {
    const args = ["run", prompt];
    if (cwd) args.push("--cwd", cwd);
    return args;
  },
  interruptSignal: "SIGINT",
};

const GEMINI_CLI_ADAPTER: CLIAdapter = {
  name: "gemini-cli",
  command: "gemini",
  defaultArgs: ["-p"],
  buildArgs(prompt, cwd) {
    const args = ["-p", prompt];
    if (cwd) args.push("--sandbox", "false");
    return args;
  },
  env: { GEMINI_MODEL: "gemini-2.5-pro" },
  interruptSignal: "SIGINT",
};

const CODEX_CLI_ADAPTER: CLIAdapter = {
  name: "codex-cli",
  command: "codex",
  defaultArgs: ["exec"],
  buildArgs(prompt, cwd) {
    const args = ["exec", prompt];
    if (cwd) args.push("--cwd", cwd);
    return args;
  },
  env: { CODEX_MODEL: "o3" },
  interruptSignal: "SIGINT",
};

// ---------------------------------------------------------------------------
// CLIController
// ---------------------------------------------------------------------------

export class CLIController extends EventEmitter {
  private adapters: Map<string, CLIAdapter> = new Map();
  private processes: Map<string, CLIProcess> = new Map();
  private maxConcurrent: number;
  private outputLimit: number; // max lines to retain per process

  constructor(config?: { maxConcurrent?: number; outputLimit?: number }) {
    super();
    this.maxConcurrent = config?.maxConcurrent ?? 8;
    this.outputLimit = config?.outputLimit ?? 1000;
    this.registerDefaultAdapters();
  }

  // -- Adapter registry -----------------------------------------------------

  private registerDefaultAdapters(): void {
    this.registerAdapter(CLAUDE_CODE_ADAPTER);
    this.registerAdapter(OPENCODE_ADAPTER);
    this.registerAdapter(GEMINI_CLI_ADAPTER);
    this.registerAdapter(CODEX_CLI_ADAPTER);
  }

  registerAdapter(adapter: CLIAdapter): void {
    this.adapters.set(adapter.name, adapter);
    this.emit("adapter-registered", adapter.name);
  }

  getAdapter(name: string): CLIAdapter | undefined {
    return this.adapters.get(name);
  }

  getAdapters(): CLIAdapter[] {
    return Array.from(this.adapters.values());
  }

  // -- Process lifecycle ----------------------------------------------------

  /**
   * Spawn a CLI process for a worker.
   */
  spawn(workerId: string, cliName: string, prompt: string, cwd?: string): CLIProcess | null {
    // Check concurrency
    const active = Array.from(this.processes.values()).filter(
      (p) => p.status === "running" || p.status === "spawning"
    );
    if (active.length >= this.maxConcurrent) {
      this.emit("spawn-blocked", { workerId, reason: "max-concurrent-reached" });
      return null;
    }

    const adapter = this.adapters.get(cliName);
    if (!adapter) {
      this.emit("spawn-error", { workerId, error: `Unknown CLI: ${cliName}` });
      return null;
    }

    const args = adapter.buildArgs(prompt, cwd);
    const env = { ...process.env, ...adapter.env };

    const cliProcess: CLIProcess = {
      workerId,
      cliName,
      status: "spawning",
      startedAt: Date.now(),
      lastOutput: Date.now(),
      stdout: [],
      stderr: [],
    };

    try {
      const child = spawn(adapter.command, args, {
        env,
        stdio: ["pipe", "pipe", "pipe"],
        detached: false,
        shell: process.platform === "win32",
      });

      cliProcess.process = child;
      cliProcess.pid = child.pid;
      cliProcess.status = "running";

      // Collect stdout
      child.stdout?.on("data", (data: Buffer) => {
        const lines = data.toString("utf-8").split("\n").filter(Boolean);
        cliProcess.stdout.push(...lines);
        if (cliProcess.stdout.length > this.outputLimit) {
          cliProcess.stdout = cliProcess.stdout.slice(-this.outputLimit);
        }
        cliProcess.lastOutput = Date.now();
        this.emit("output", { workerId, stream: "stdout", lines });

        // Check completion pattern
        if (adapter.completionPattern) {
          const fullOutput = cliProcess.stdout.join("\n");
          if (adapter.completionPattern.test(fullOutput)) {
            this.handleCompletion(workerId, 0);
          }
        }
      });

      // Collect stderr
      child.stderr?.on("data", (data: Buffer) => {
        const lines = data.toString("utf-8").split("\n").filter(Boolean);
        cliProcess.stderr.push(...lines);
        if (cliProcess.stderr.length > this.outputLimit) {
          cliProcess.stderr = cliProcess.stderr.slice(-this.outputLimit);
        }
        cliProcess.lastOutput = Date.now();
        this.emit("output", { workerId, stream: "stderr", lines });
      });

      // Handle exit
      child.on("exit", (code, signal) => {
        this.handleExit(workerId, code, signal);
      });

      child.on("error", (err) => {
        cliProcess.status = "error";
        cliProcess.error = err.message;
        this.emit("process-error", { workerId, error: err.message });
      });

      this.processes.set(workerId, cliProcess);
      this.emit("process-spawned", { workerId, cliName, pid: child.pid });
      return cliProcess;
    } catch (err: any) {
      cliProcess.status = "error";
      cliProcess.error = err.message;
      this.processes.set(workerId, cliProcess);
      this.emit("spawn-error", { workerId, error: err.message });
      return cliProcess;
    }
  }

  /**
   * Stop a running process.
   */
  stop(workerId: string): boolean {
    const proc = this.processes.get(workerId);
    if (!proc) return false;
    if (proc.status !== "running" && proc.status !== "spawning") return false;

    const adapter = this.adapters.get(proc.cliName);
    const signal = adapter?.interruptSignal ?? "SIGTERM";

    if (proc.process && !proc.process.killed) {
      proc.process.kill(signal);
    }
    proc.status = "stopped";
    this.emit("process-stopped", { workerId });
    return true;
  }

  /**
   * Send input to a running process stdin.
   */
  sendInput(workerId: string, input: string): boolean {
    const proc = this.processes.get(workerId);
    if (!proc || proc.status !== "running" || !proc.process?.stdin) return false;
    proc.process.stdin.write(input + "\n");
    return true;
  }

  /**
   * Get the output of a process.
   */
  getOutput(workerId: string): { stdout: string[]; stderr: string[] } | null {
    const proc = this.processes.get(workerId);
    if (!proc) return null;
    return { stdout: [...proc.stdout], stderr: [...proc.stderr] };
  }

  /**
   * Get the last N lines of output.
   */
  getTailOutput(workerId: string, lines: number = 50): { stdout: string[]; stderr: string[] } | null {
    const proc = this.processes.get(workerId);
    if (!proc) return null;
    return {
      stdout: proc.stdout.slice(-lines),
      stderr: proc.stderr.slice(-lines),
    };
  }

  /**
   * Get all active processes.
   */
  getActiveProcesses(): CLIProcess[] {
    return Array.from(this.processes.values()).filter(
      (p) => p.status === "running" || p.status === "spawning"
    );
  }

  /**
   * Get a process by worker ID.
   */
  getProcess(workerId: string): CLIProcess | undefined {
    return this.processes.get(workerId);
  }

  /**
   * Stop all processes.
   */
  stopAll(): void {
    for (const [workerId, proc] of this.processes) {
      if (proc.status === "running" || proc.status === "spawning") {
        this.stop(workerId);
      }
    }
  }

  // -- Internal handlers ----------------------------------------------------

  private handleCompletion(workerId: string, exitCode: number): void {
    const proc = this.processes.get(workerId);
    if (!proc) return;
    proc.status = "completing";
    proc.exitCode = exitCode;
    this.emit("process-completing", { workerId, exitCode });
  }

  private handleExit(workerId: string, code: number | null, signal: NodeJS.Signals | null): void {
    const proc = this.processes.get(workerId);
    if (!proc) return;

    proc.exitCode = code ?? undefined;
    proc.process = undefined;
    proc.pid = undefined;

    if (proc.status === "completing" || proc.status === "stopped") {
      // Normal completion or intentional stop
      proc.status = code === 0 ? "idle" : "stopped";
    } else {
      proc.status = code === 0 ? "idle" : "error";
      if (code !== 0) {
        proc.error = `Exited with code ${code}` + (signal ? ` (signal: ${signal})` : "");
      }
    }

    this.emit("process-exited", { workerId, code, signal, status: proc.status });
  }

  // -- State ----------------------------------------------------------------

  getState(): CLIControllerState {
    const procs = Array.from(this.processes.values());
    return {
      totalProcesses: procs.length,
      activeProcesses: procs.filter((p) => p.status === "running" || p.status === "spawning").length,
      stoppedProcesses: procs.filter((p) => p.status === "stopped").length,
      errorProcesses: procs.filter((p) => p.status === "error").length,
    };
  }

  destroy(): void {
    this.stopAll();
    this.processes.clear();
  }
}

export default CLIController;
