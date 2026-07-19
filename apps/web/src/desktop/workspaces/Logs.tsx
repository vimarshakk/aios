"use client";

import { useState, useEffect, useRef } from "react";
import { api, type GoalSnapshot } from "@/lib/api";
import {
  ScrollText, Search, Filter, Trash2, Download, Pause, Play,
  AlertTriangle, Info, AlertCircle, Bug, Loader2,
} from "lucide-react";

type LogLevel = "info" | "warn" | "error" | "debug";

interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  source: string;
  message: string;
}

const LEVEL_CONFIG: Record<LogLevel, { icon: React.ComponentType<{ size?: number }>; color: string }> = {
  info: { icon: Info, color: "var(--green)" },
  warn: { icon: AlertTriangle, color: "var(--yellow)" },
  error: { icon: AlertCircle, color: "var(--red)" },
  debug: { icon: Bug, color: "var(--text-muted)" },
};

function snapToLog(snap: GoalSnapshot): LogEntry {
  const status = snap.status ?? "planning";
  let level: LogLevel = "info";
  let message = `Goal "${snap.objective}" — ${status}`;
  if (status === "failed") { level = "error"; message = `Goal failed: ${snap.error ?? snap.objective}`; }
  else if (status === "completed") { message = `Goal completed: ${snap.objective}`; }
  else if (status === "planning") { level = "debug"; message = `Planning: ${snap.objective}`; }
  else if (status === "in_progress") { message = `Executing: ${snap.objective}`; }
  else if (status === "cancelled") { level = "warn"; message = `Goal cancelled: ${snap.objective}`; }

  const steps = snap.steps ?? [];
  const completedSteps = steps.filter((s) => s.status === "completed").length;
  if (steps.length > 0) {
    message += ` [${completedSteps}/${steps.length} steps]`;
  }

  return {
    id: snap.goal_id + "-" + Date.now(),
    timestamp: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    level,
    source: "goal-engine",
    message,
  };
}

export function LogsWorkspace() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filterLevel, setFilterLevel] = useState<LogLevel | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [paused, setPaused] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const pausedRef = useRef(paused);
  pausedRef.current = paused;

  useEffect(() => {
    const unsub = api.subscribeAllGoals(
      (goals) => {
        if (pausedRef.current) return;
        const newLogs = goals.map(snapToLog);
        setLogs((prev) => {
          const merged = [...prev, ...newLogs];
          return merged.slice(-500);
        });
      },
      () => {},
      () => {},
    );
    return unsub;
  }, []);

  useEffect(() => {
    if (!paused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, paused]);

  const filtered = logs.filter((l) => {
    if (filterLevel && l.level !== filterLevel) return false;
    if (searchQuery && !l.message.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const selectedLog = logs.find((l) => l.id === selectedId);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-6 py-3 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2">
          {(["info", "warn", "error", "debug"] as const).map((level) => {
            const cfg = LEVEL_CONFIG[level];
            const Icon = cfg.icon;
            return (
              <button
                key={level}
                className={`logs-level-btn ${filterLevel === level ? "active" : ""}`}
                onClick={() => setFilterLevel(filterLevel === level ? null : level)}
                style={filterLevel === level ? { borderColor: cfg.color, color: cfg.color } : {}}
              >
                <Icon size={12} />
                {level}
              </button>
            );
          })}
        </div>
        <div className="flex-1" />
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter logs…"
            className="logs-search"
          />
        </div>
        <button
          className="btn-icon"
          style={{ border: "none" }}
          onClick={() => setPaused(!paused)}
          title={paused ? "Resume" : "Pause"}
        >
          {paused ? <Play size={14} /> : <Pause size={14} />}
        </button>
        <button className="btn-icon" style={{ border: "none" }} title="Clear" onClick={() => setLogs([])}>
          <Trash2 size={14} />
        </button>
      </div>

      {/* Log content */}
      <div className="flex flex-1 min-h-0">
        {/* Log list */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto font-mono text-xs">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 gap-3">
              <span style={{ color: "var(--text-muted)" }}><ScrollText size={28} /></span>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                {searchQuery || filterLevel ? "No matching logs" : "Waiting for goal events…"}
              </p>
            </div>
          ) : filtered.map((log) => {
            const cfg = LEVEL_CONFIG[log.level];
            const Icon = cfg.icon;
            const isSelected = selectedId === log.id;
            return (
              <button
                key={log.id}
                className={`logs-row ${isSelected ? "selected" : ""}`}
                onClick={() => setSelectedId(log.id)}
              >
                <span className="logs-timestamp">{log.timestamp}</span>
                <span style={{ color: cfg.color }}><Icon size={12} /></span>
                <span className="logs-source">{log.source}</span>
                <span className="logs-message">{log.message}</span>
              </button>
            );
          })}
        </div>

        {/* Log detail */}
        {selectedLog && (
          <div
            className="w-72 shrink-0 overflow-y-auto p-4"
            style={{ borderLeft: "1px solid var(--border)", background: "var(--bg-subtle)" }}
          >
            <h4 className="text-xs font-semibold mb-3" style={{ color: "var(--text-muted)" }}>
              Log Detail
            </h4>
            <div className="space-y-2">
              <div>
                <label className="settings-label">Time</label>
                <p className="text-sm mt-1" style={{ color: "var(--text-primary)" }}>{selectedLog.timestamp}</p>
              </div>
              <div>
                <label className="settings-label">Level</label>
                <p className="text-sm mt-1" style={{ color: LEVEL_CONFIG[selectedLog.level].color }}>{selectedLog.level.toUpperCase()}</p>
              </div>
              <div>
                <label className="settings-label">Source</label>
                <p className="text-sm mt-1" style={{ color: "var(--text-primary)" }}>{selectedLog.source}</p>
              </div>
              <div>
                <label className="settings-label">Message</label>
                <p className="text-sm mt-1" style={{ color: "var(--text-primary)" }}>{selectedLog.message}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Status bar */}
      <div className="flex items-center justify-between px-6 py-2 shrink-0" style={{ borderTop: "1px solid var(--border)", background: "var(--bg-subtle)" }}>
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {filtered.length} entries
          {filterLevel && ` (filtered by ${filterLevel})`}
          {searchQuery && ` matching "${searchQuery}"`}
        </span>
        <span className="text-xs" style={{ color: paused ? "var(--yellow)" : "var(--green)" }}>
          {paused ? "⏸ Paused" : "● Live"}
        </span>
      </div>
    </div>
  );
}
