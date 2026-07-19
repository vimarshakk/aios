"use client";

import { useState, useEffect, useCallback } from "react";
import { WorkforcePanel } from "../components/devmode/WorkforcePanel";
import { TaskGraph } from "../components/devmode/TaskGraph";
import { api } from "@/lib/api";
import type { Worker, WorkerRole, TaskNode } from "../types";
import { Users, GitBranch, Zap, Clock, Coins } from "lucide-react";

export function WorkforceWorkspace() {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [tasks, setTasks] = useState<TaskNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [subTab, setSubTab] = useState<"workers" | "graph">("workers");

  const fetchData = useCallback(async () => {
    try {
      const res = await api.workforce.listWorkers();
      const mapped: Worker[] = (Array.isArray(res) ? res : []).map((w: Record<string, unknown>) => ({
        id: w.id as string,
        name: (w.role as string) || (w.id as string),
        type: "cli" as const,
        command: (w.cli as string) || "",
        status: (w.status as string) === "running" ? "running" : (w.status as string) === "error" ? "error" : (w.status as string) === "busy" ? "busy" : "idle",
        role: ((w.role as string) || "backend") as WorkerRole,
        capabilities: ((w.capabilities as string[]) || []).map((c) => ({
          name: c, description: c, level: "primary" as const,
        })),
        assignedTask: undefined,
        tokensUsed: 0,
        cost: 0,
        lastActive: Date.now(),
      }));
      setWorkers(mapped);
      setLoading(false);
      setError(null);
    } catch (e) {
      setError(String(e));
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

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
        <button onClick={fetchData} style={{ marginTop: "8px", padding: "6px 14px", borderRadius: "6px", background: "var(--accent)", color: "#fff", border: "none", fontSize: "0.75rem", cursor: "pointer" }}>
          Retry
        </button>
      </div>
    );
  }

  const running = workers.filter((w) => w.status === "running" || w.status === "busy").length;
  const totalTokens = workers.reduce((s, w) => s + w.tokensUsed, 0);
  const totalCost = workers.reduce((s, w) => s + w.cost, 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", borderBottom: "1px solid var(--border)", background: "var(--bg-subtle)", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ color: "var(--accent)", display: "inline-flex" }}><Users size={16} /></span>
          <span style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>Workforce</span>
          <span style={{ fontSize: "0.65rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", padding: "2px 6px", borderRadius: "4px", background: running > 0 ? "rgba(16, 185, 129, 0.15)" : "var(--surface)", color: running > 0 ? "var(--green)" : "var(--text-muted)", border: `1px solid ${running > 0 ? "rgba(16, 185, 129, 0.3)" : "var(--border)"}` }}>
            {running}/{workers.length} active
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "16px", fontSize: "0.72rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--text-secondary)" }}>
            <Zap size={12} /><span>{tasks.length} tasks</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--text-secondary)" }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem" }}>{totalTokens.toLocaleString()} tokens</span>
            <span style={{ color: "var(--accent)", fontWeight: 600 }}>${totalCost.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Sub-tab bar */}
      <div style={{ display: "flex", alignItems: "center", gap: "0", padding: "0 16px", borderBottom: "1px solid var(--border)", background: "var(--bg)", flexShrink: 0 }}>
        {([
          { id: "workers" as const, label: "Workers", icon: Users },
          { id: "graph" as const, label: "Task Graph", icon: GitBranch },
        ]).map((tab) => {
          const Icon = tab.icon;
          const active = subTab === tab.id;
          return (
            <button key={tab.id} onClick={() => setSubTab(tab.id)} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "10px 14px", fontSize: "0.78rem", fontWeight: active ? 600 : 400, color: active ? "var(--text-primary)" : "var(--text-secondary)", background: "none", border: "none", borderBottom: active ? "2px solid var(--accent)" : "2px solid transparent", cursor: "pointer", transition: "all 0.15s ease", whiteSpace: "nowrap" }}>
              <Icon size={14} />{tab.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: "auto" }}>
        {subTab === "workers" ? <WorkforcePanel workers={workers} /> : <TaskGraph tasks={tasks} workers={workers} />}
      </div>
    </div>
  );
}

export default WorkforceWorkspace;
