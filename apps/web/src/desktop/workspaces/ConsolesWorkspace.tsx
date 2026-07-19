"use client";

import { useState, useEffect, useCallback } from "react";
import { LiveConsole } from "../components/devmode/LiveConsole";
import { api } from "@/lib/api";
import type { Worker } from "../types";
import { Terminal, Cpu, Clock, Zap } from "lucide-react";

export function ConsolesWorkspace() {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState("0m 00s");

  const fetchData = useCallback(async () => {
    try {
      const res = await api.workforce.listWorkers();
      const mapped: Worker[] = (Array.isArray(res) ? res : []).map((w: Record<string, unknown>) => ({
        id: w.id as string,
        name: (w.role as string) || (w.id as string),
        type: "cli" as const,
        command: (w.cli as string) || "",
        status: (w.status as string) === "running" ? "running" : (w.status as string) === "error" ? "error" : (w.status as string) === "busy" ? "busy" : "idle",
        role: (w.role as string) || "backend",
        capabilities: [],
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

  // Timer
  useEffect(() => {
    const start = Date.now();
    const interval = setInterval(() => {
      const secs = Math.floor((Date.now() - start) / 1000);
      setElapsed(`${Math.floor(secs / 60)}m ${(secs % 60).toString().padStart(2, "0")}s`);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)" }}>
        <span style={{ fontSize: "0.85rem" }}>Loading consoles...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)", gap: "8px" }}>
        <span style={{ fontSize: "0.85rem" }}>Could not load consoles</span>
        <span style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>{error}</span>
        <button onClick={fetchData} style={{ marginTop: "8px", padding: "6px 14px", borderRadius: "6px", background: "var(--accent)", color: "#fff", border: "none", fontSize: "0.75rem", cursor: "pointer" }}>Retry</button>
      </div>
    );
  }

  const running = workers.filter((w) => w.status === "running" || w.status === "busy").length;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", borderBottom: "1px solid var(--border)", background: "var(--bg-subtle)", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ color: "var(--accent)", display: "inline-flex" }}><Terminal size={16} /></span>
          <span style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>Consoles</span>
          <span style={{ fontSize: "0.65rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", padding: "2px 6px", borderRadius: "4px", background: running > 0 ? "rgba(16, 185, 129, 0.15)" : "var(--surface)", color: running > 0 ? "var(--green)" : "var(--text-muted)" }}>
            {running} running
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "0.72rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--text-secondary)" }}>
            <Cpu size={12} /><span>{workers.length} workers</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--text-secondary)" }}>
            <Clock size={12} /><span>{elapsed}</span>
          </div>
        </div>
      </div>

      {/* Console content */}
      <div style={{ flex: 1, overflow: "hidden" }}>
        <LiveConsole workers={workers} />
      </div>
    </div>
  );
}

export default ConsolesWorkspace;
