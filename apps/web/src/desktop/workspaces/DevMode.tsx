"use client";

import { useState, useEffect, useCallback } from "react";
import { useWorkspaceStore } from "../state/workspace";
import { WorkforcePanel } from "../components/devmode/WorkforcePanel";
import { TaskGraph } from "../components/devmode/TaskGraph";
import { LiveConsole } from "../components/devmode/LiveConsole";
import { ReviewPanel } from "../components/devmode/ReviewPanel";
import { BuildArtifacts } from "../components/devmode/BuildArtifacts";
import { api } from "@/lib/api";
import type { Worker, TaskNode, ReviewRequest, BuildArtifact } from "../types";
import {
  Users, GitBranch, Terminal, CheckCircle2, Package,
  Command, Cpu, Zap, Clock,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Dev Mode tabs
// ---------------------------------------------------------------------------

const DEV_TABS = [
  { id: "workforce", label: "Workforce", icon: Users },
  { id: "task-graph", label: "Task Graph", icon: GitBranch },
  { id: "consoles", label: "Consoles", icon: Terminal },
  { id: "reviews", label: "Reviews", icon: CheckCircle2 },
  { id: "artifacts", label: "Artifacts", icon: Package },
] as const;

type DevTab = (typeof DEV_TABS)[number]["id"];

// ---------------------------------------------------------------------------
// Status bar helper
// ---------------------------------------------------------------------------

function WorkerCountBadge({ workers }: { workers: Worker[] }) {
  const running = workers.filter((w) => w.status === "running" || w.status === "busy").length;
  const total = workers.length;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "4px",
        padding: "2px 8px",
        borderRadius: "9999px",
        fontSize: "0.7rem",
        fontWeight: 600,
        background: running > 0 ? "rgba(16, 185, 129, 0.15)" : "var(--surface)",
        color: running > 0 ? "var(--green)" : "var(--text-muted)",
        border: `1px solid ${running > 0 ? "rgba(16, 185, 129, 0.3)" : "var(--border)"}`,
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: "currentColor",
          animation: running > 0 ? "pulse 2s ease-in-out infinite" : "none",
        }}
      />
      {running}/{total}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Dev Mode Workspace
// ---------------------------------------------------------------------------

export function DevModeWorkspace() {
  const { devModeTab, setDevModeTab } = useWorkspaceStore();

  const [workers, setWorkers] = useState<Worker[]>([]);
  const [tasks, setTasks] = useState<TaskNode[]>([]);
  const [reviews, setReviews] = useState<ReviewRequest[]>([]);
  const [artifacts, setArtifacts] = useState<BuildArtifact[]>([]);
  const [elapsed, setElapsed] = useState("0m 00s");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch workforce data from gateway on mount and every 10s
  const fetchWorkforce = useCallback(async () => {
    try {
      const res = await api.workforce.listWorkers();
      if (res.ok) {
        const mapped: Worker[] = res.workers.map((w: Record<string, unknown>) => ({
          id: w.id as string,
          name: w.name as string,
          type: "cli" as const,
          command: (w.cli as string) || "",
          status: (w.status as string) === "running" ? "running" : (w.status as string) === "error" ? "error" : (w.status as string) === "busy" ? "busy" : "idle",
          role: (w.role as string) || "backend",
          capabilities: ((w.capabilities as string[]) || []).map((c) => ({
            name: c, description: c, level: "primary" as const,
          })),
          assignedTask: undefined,
          tokensUsed: (w.tasksCompleted as number) || 0,
          cost: 0,
          lastActive: (w.lastActive as number) || Date.now(),
        }));
        setWorkers(mapped);
        setLoading(false);
        setError(null);
      }
    } catch (e) {
      setError(String(e));
      setLoading(false);
    }
  }, []);

  // Fetch active reviews
  const fetchReviews = useCallback(async () => {
    try {
      const res = await api.reviews.listActive();
      if (res.ok) {
        const mapped: ReviewRequest[] = Object.values(res.reviews).map((r: Record<string, unknown>) => ({
          id: r.id as string,
          taskId: "",
          taskName: (r.title as string) || "",
          sourceWorker: (r.authorWorkerId as string) || "",
          reviewWorker: (r.reviewerWorkerId as string) || "",
          sourceOutput: (r.outputSummary as string) || "",
          status: (r.status as string) as ReviewRequest["status"],
          reviewNotes: (r.verdictReason as string) || "",
          createdAt: r.createdAt as number,
          completedAt: r.completedAt as number,
        }));
        setReviews(mapped);
      }
    } catch {
      // Non-critical — keep showing current reviews
    }
  }, []);

  // Fetch data on mount and poll workforce
  useEffect(() => {
    fetchWorkforce();
    fetchReviews();
    const interval = setInterval(fetchWorkforce, 10000);
    const reviewInterval = setInterval(fetchReviews, 15000);
    return () => { clearInterval(interval); clearInterval(reviewInterval); };
  }, [fetchWorkforce, fetchReviews]);

  // Timer
  useEffect(() => {
    const start = Date.now();
    const interval = setInterval(() => {
      const secs = Math.floor((Date.now() - start) / 1000);
      setElapsed(`${Math.floor(secs / 60)}m ${(secs % 60).toString().padStart(2, "0")}s`);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const activeWorkers = workers.filter((w) => w.status === "running" || w.status === "busy").length;
  const completedTasks = tasks.filter((t) => t.status === "completed").length;
  const totalTokens = workers.reduce((s, w) => s + w.tokensUsed, 0);
  const totalCost = workers.reduce((s, w) => s + w.cost, 0);

  const renderTab = useCallback(() => {
    switch (devModeTab) {
      case "workforce":
        return <WorkforcePanel workers={workers} />;
      case "task-graph":
        return <TaskGraph tasks={tasks} workers={workers} />;
      case "consoles":
        return <LiveConsole workers={workers} />;
      case "reviews":
        return <ReviewPanel reviews={reviews} />;
      case "artifacts":
        return <BuildArtifacts artifacts={artifacts} />;
      default:
        return <WorkforcePanel workers={workers} />;
    }
  }, [devModeTab, workers, tasks, reviews, artifacts]);

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)" }}>
        <span style={{ fontSize: "0.85rem" }}>Loading workforce...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)", gap: "8px" }}>
        <span style={{ fontSize: "0.85rem" }}>Could not connect to gateway</span>
        <span style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>{error}</span>
        <button
          onClick={fetchWorkforce}
          style={{
            marginTop: "8px", padding: "6px 14px", borderRadius: "6px",
            background: "var(--accent)", color: "#fff", border: "none", fontSize: "0.75rem", cursor: "pointer",
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 16px",
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-subtle)",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Command size={16} style={{ color: "var(--accent)" }} />
          <span style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>
            Developer Mode
          </span>
          <span
            style={{
              fontSize: "0.65rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              padding: "2px 6px",
              borderRadius: "4px",
              background: "var(--accent)",
              color: "#fff",
            }}
          >
            Active
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "16px", fontSize: "0.75rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--text-secondary)" }}>
            <Cpu size={12} />
            <span>{activeWorkers} workers active</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--text-secondary)" }}>
            <Zap size={12} />
            <span>{completedTasks}/{tasks.length} tasks</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--text-secondary)" }}>
            <Clock size={12} />
            <span>{elapsed}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--text-secondary)" }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem" }}>
              {totalTokens.toLocaleString()} tokens
            </span>
            <span style={{ color: "var(--accent)", fontWeight: 600 }}>
              ${totalCost.toFixed(2)}
            </span>
          </div>
          <WorkerCountBadge workers={workers} />
        </div>
      </div>

      {/* Tab bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0",
          padding: "0 16px",
          borderBottom: "1px solid var(--border)",
          background: "var(--bg)",
          flexShrink: 0,
        }}
      >
        {DEV_TABS.map((tab) => {
          const Icon = tab.icon;
          const active = devModeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setDevModeTab(tab.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "10px 14px",
                fontSize: "0.78rem",
                fontWeight: active ? 600 : 400,
                color: active ? "var(--text-primary)" : "var(--text-secondary)",
                background: "none",
                border: "none",
                borderBottom: active ? "2px solid var(--accent)" : "2px solid transparent",
                cursor: "pointer",
                transition: "all 0.15s ease",
                whiteSpace: "nowrap",
              }}
            >
              <Icon size={14} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflow: "auto", padding: "0" }}>
        {renderTab()}
      </div>
    </div>
  );
}

export default DevModeWorkspace;
