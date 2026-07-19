"use client";

import { useState, useMemo } from "react";
import type { TaskNode, Worker } from "../../types";
import {
  GitBranch, CheckCircle2, Clock, AlertCircle, Loader2,
  Circle, ChevronRight, Eye, Users,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Status config
// ---------------------------------------------------------------------------

const TASK_STATUS: Record<string, { icon: React.ComponentType<{ size?: number }>; color: string; bg: string }> = {
  pending: { icon: Circle, color: "var(--text-muted)", bg: "var(--surface)" },
  assigned: { icon: Clock, color: "#f59e0b", bg: "rgba(245, 158, 11, 0.1)" },
  running: { icon: Loader2, color: "var(--accent)", bg: "rgba(224, 94, 56, 0.1)" },
  completed: { icon: CheckCircle2, color: "var(--green)", bg: "rgba(16, 185, 129, 0.1)" },
  failed: { icon: AlertCircle, color: "#ef4444", bg: "rgba(239, 68, 68, 0.1)" },
  reviewing: { icon: Eye, color: "#8b5cf6", bg: "rgba(139, 92, 246, 0.1)" },
  approved: { icon: CheckCircle2, color: "var(--green)", bg: "rgba(16, 185, 129, 0.1)" },
};

const ROLE_COLORS: Record<string, string> = {
  architect: "#e05e38",
  backend: "#3b82f6",
  frontend: "#8b5cf6",
  qa: "#10b981",
  devops: "#f59e0b",
  researcher: "#06b6d4",
  designer: "#ec4899",
  reviewer: "#8b5cf6",
};

// ---------------------------------------------------------------------------
// Task node (single row)
// ---------------------------------------------------------------------------

function TaskRow({ task, workers, isLast }: { task: TaskNode; workers: Worker[]; isLast: boolean }) {
  const cfg = TASK_STATUS[task.status] ?? TASK_STATUS.pending;
  const Icon = cfg.icon;
  const worker = workers.find((w) => w.id === task.assignedWorker);
  const roleColor = ROLE_COLORS[task.workerRole] ?? "var(--text-muted)";

  return (
    <div style={{ display: "flex", gap: "0", position: "relative" }}>
      {/* Timeline line + dot */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          width: "32px",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: 24,
            height: 24,
            borderRadius: "50%",
            background: cfg.bg,
            border: `2px solid ${cfg.color}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            zIndex: 1,
          }}
        >
          <span
            style={{
              color: cfg.color,
              animation: task.status === "running" ? "spin 1s linear infinite" : "none",
              display: "inline-flex",
            }}
          >
            <Icon size={12} />
          </span>
        </div>
        {!isLast && (
          <div
            style={{
              width: 2,
              flex: 1,
              background: "var(--border)",
              marginTop: 4,
            }}
          />
        )}
      </div>

      {/* Task content */}
      <div
        style={{
          flex: 1,
          padding: "4px 0 16px 12px",
          minWidth: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>
            {task.name}
          </span>
          <span
            style={{
              padding: "1px 6px",
              borderRadius: "9999px",
              fontSize: "0.62rem",
              fontWeight: 600,
              background: `${roleColor}15`,
              color: roleColor,
              border: `1px solid ${roleColor}30`,
              textTransform: "capitalize",
            }}
          >
            {task.workerRole}
          </span>
        </div>

        {worker && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              marginTop: "4px",
              fontSize: "0.72rem",
              color: "var(--text-secondary)",
            }}
          >
            <Users size={11} />
            <span>{worker.name}</span>
          </div>
        )}

        {task.dependencies.length > 0 && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              marginTop: "4px",
              fontSize: "0.65rem",
              color: "var(--text-muted)",
            }}
          >
            <ChevronRight size={10} />
            <span>depends on: {task.dependencies.join(", ")}</span>
          </div>
        )}

        {task.error && (
          <div
            style={{
              marginTop: "6px",
              padding: "6px 8px",
              borderRadius: "var(--radius-sm)",
              background: "rgba(239, 68, 68, 0.08)",
              border: "1px solid rgba(239, 68, 68, 0.2)",
              fontSize: "0.72rem",
              color: "#ef4444",
              fontFamily: "var(--font-mono)",
            }}
          >
            {task.error}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// TaskGraph
// ---------------------------------------------------------------------------

export function TaskGraph({ tasks, workers }: { tasks: TaskNode[]; workers: Worker[] }) {
  const completed = tasks.filter((t) => t.status === "completed" || t.status === "approved").length;
  const total = tasks.length;
  const progress = total > 0 ? Math.round((completed / total) * 100) : 0;

  // Build adjacency for dependency visualization
  const sorted = useMemo(() => {
    const result: TaskNode[] = [];
    const visited = new Set<string>();

    function visit(id: string) {
      if (visited.has(id)) return;
      visited.add(id);
      const task = tasks.find((t) => t.id === id);
      if (!task) return;
      for (const dep of task.dependencies) visit(dep);
      result.push(task);
    }

    for (const t of tasks) visit(t.id);
    return result;
  }, [tasks]);

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "16px", height: "100%" }}>
      {/* Progress header */}
      <div
        style={{
          padding: "12px 16px",
          borderRadius: "var(--radius-md)",
          background: "var(--bg-subtle)",
          border: "1px solid var(--border)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>
            Execution Graph
          </span>
          <span style={{ fontSize: "0.72rem", fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
            {completed}/{total} tasks
          </span>
        </div>
        <div
          style={{
            height: 6,
            borderRadius: 3,
            background: "var(--surface)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${progress}%`,
              borderRadius: 3,
              background: "linear-gradient(90deg, var(--accent), var(--accent-hover))",
              transition: "width 0.5s ease",
            }}
          />
        </div>
      </div>

      {/* Task timeline */}
      <div style={{ flex: 1, overflow: "auto" }}>
        {sorted.map((task, i) => (
          <TaskRow
            key={task.id}
            task={task}
            workers={workers}
            isLast={i === sorted.length - 1}
          />
        ))}
        {tasks.length === 0 && (
          <div
            style={{
              padding: "48px",
              textAlign: "center",
              color: "var(--text-muted)",
              fontSize: "0.82rem",
            }}
          >
            No tasks in the execution graph yet.
            <br />
            <span style={{ fontSize: "0.72rem" }}>
              Submit a goal to generate the task DAG.
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
