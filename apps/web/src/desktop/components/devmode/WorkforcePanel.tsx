"use client";

import { useState } from "react";
import type { Worker } from "../../types";
import {
  Play, Square, RotateCcw, Terminal, Cpu, Zap, Clock,
  ChevronDown, ChevronRight, ExternalLink, Activity, Coins,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Status config
// ---------------------------------------------------------------------------

const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string; pulse: boolean }> = {
  running: { color: "#10b981", bg: "rgba(16, 185, 129, 0.12)", label: "Running", pulse: true },
  busy: { color: "#f59e0b", bg: "rgba(245, 158, 11, 0.12)", label: "Busy", pulse: true },
  idle: { color: "var(--text-muted)", bg: "var(--surface)", label: "Idle", pulse: false },
  offline: { color: "var(--text-muted)", bg: "var(--surface)", label: "Offline", pulse: false },
  error: { color: "#ef4444", bg: "rgba(239, 68, 68, 0.12)", label: "Error", pulse: false },
};

const ROLE_ICONS: Record<string, string> = {
  architect: "🏗️",
  backend: "⚙️",
  frontend: "🎨",
  qa: "🧪",
  devops: "🚀",
  researcher: "🔍",
  designer: "✏️",
  reviewer: "👁️",
};

// ---------------------------------------------------------------------------
// Worker card
// ---------------------------------------------------------------------------

function WorkerCard({ worker, expanded, onToggle }: {
  worker: Worker;
  expanded: boolean;
  onToggle: () => void;
}) {
  const cfg = STATUS_CONFIG[worker.status] ?? STATUS_CONFIG.idle;
  const roleIcon = ROLE_ICONS[worker.role] ?? "🔧";

  const elapsed = worker.startedAt
    ? Math.floor((Date.now() - worker.startedAt) / 1000)
    : 0;
  const elapsedStr = elapsed >= 60
    ? `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`
    : `${elapsed}s`;

  return (
    <div
      style={{
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border)",
        background: "var(--bg-subtle)",
        overflow: "hidden",
        transition: "border-color 0.15s ease",
      }}
    >
      {/* Header row */}
      <button
        onClick={onToggle}
        style={{
          display: "flex",
          alignItems: "center",
          width: "100%",
          padding: "10px 12px",
          gap: "10px",
          background: "none",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span style={{ fontSize: "1.1rem" }}>{roleIcon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>
              {worker.name}
            </span>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                padding: "1px 6px",
                borderRadius: "9999px",
                fontSize: "0.65rem",
                fontWeight: 600,
                background: cfg.bg,
                color: cfg.color,
              }}
            >
              {cfg.pulse && (
                <span
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: "50%",
                    background: cfg.color,
                    animation: "pulse 2s ease-in-out infinite",
                  }}
                />
              )}
              {cfg.label}
            </span>
          </div>
          {worker.assignedTask && (
            <div
              style={{
                fontSize: "0.72rem",
                color: "var(--text-secondary)",
                marginTop: "2px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {worker.assignedTask}
            </div>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", flexShrink: 0 }}>
          {worker.tokensUsed > 0 && (
            <span
              style={{
                fontSize: "0.68rem",
                fontFamily: "var(--font-mono)",
                color: "var(--text-muted)",
              }}
            >
              {(worker.tokensUsed / 1000).toFixed(1)}k
            </span>
          )}
          {worker.cost > 0 && (
            <span
              style={{
                fontSize: "0.68rem",
                fontFamily: "var(--font-mono)",
                color: "var(--accent)",
                fontWeight: 600,
              }}
            >
              ${worker.cost.toFixed(2)}
            </span>
          )}
          {expanded ? (
            <span style={{ color: "var(--text-muted)", display: "inline-flex" }}>
              <ChevronDown size={14} />
            </span>
          ) : (
            <span style={{ color: "var(--text-muted)", display: "inline-flex" }}>
              <ChevronRight size={14} />
            </span>
          )}
        </div>
      </button>

      {/* Expanded details */}
      {expanded && (
        <div
          style={{
            padding: "0 12px 12px",
            borderTop: "1px solid var(--border)",
          }}
        >
          {/* Capabilities */}
          <div style={{ marginTop: "10px" }}>
            <div
              style={{
                fontSize: "0.68rem",
                fontWeight: 600,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: "6px",
              }}
            >
              Capabilities
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
              {worker.capabilities.map((cap) => (
                <span
                  key={cap.name}
                  style={{
                    padding: "2px 8px",
                    borderRadius: "9999px",
                    fontSize: "0.68rem",
                    fontWeight: 500,
                    background: cap.level === "primary" ? "rgba(224, 94, 56, 0.1)" : "var(--surface)",
                    color: cap.level === "primary" ? "var(--accent)" : "var(--text-secondary)",
                    border: `1px solid ${cap.level === "primary" ? "rgba(224, 94, 56, 0.2)" : "var(--border)"}`,
                  }}
                  title={cap.description}
                >
                  {cap.name}
                </span>
              ))}
            </div>
          </div>

          {/* Stats */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: "8px",
              marginTop: "10px",
            }}
          >
            <StatBox icon={<Terminal size={12} />} label="Command" value={worker.command} />
            <StatBox icon={<Clock size={12} />} label="Uptime" value={elapsedStr} />
            <StatBox
              icon={<Activity size={12} />}
              label="Type"
              value={worker.type.toUpperCase()}
            />
          </div>

          {/* Actions */}
          <div style={{ display: "flex", gap: "6px", marginTop: "10px" }}>
            <ActionButton icon={<Terminal size={12} />} label="Console" />
            <ActionButton icon={<ExternalLink size={12} />} label="Focus" />
            {worker.status === "running" ? (
              <ActionButton icon={<Square size={12} />} label="Stop" danger />
            ) : (
              <ActionButton icon={<Play size={12} />} label="Start" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stat box
// ---------------------------------------------------------------------------

function StatBox({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div
      style={{
        padding: "6px 8px",
        borderRadius: "var(--radius-sm)",
        background: "var(--surface)",
        border: "1px solid var(--border)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "4px", marginBottom: "2px" }}>
        <span style={{ color: "var(--text-muted)" }}>{icon}</span>
        <span style={{ fontSize: "0.62rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
          {label}
        </span>
      </div>
      <div
        style={{
          fontSize: "0.72rem",
          fontWeight: 600,
          color: "var(--text-primary)",
          fontFamily: "var(--font-mono)",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {value}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Action button
// ---------------------------------------------------------------------------

function ActionButton({ icon, label, danger }: { icon: React.ReactNode; label: string; danger?: boolean }) {
  return (
    <button
      style={{
        display: "flex",
        alignItems: "center",
        gap: "4px",
        padding: "4px 10px",
        borderRadius: "var(--radius-sm)",
        fontSize: "0.68rem",
        fontWeight: 500,
        background: danger ? "rgba(239, 68, 68, 0.1)" : "var(--surface)",
        color: danger ? "#ef4444" : "var(--text-secondary)",
        border: `1px solid ${danger ? "rgba(239, 68, 68, 0.2)" : "var(--border)"}`,
        cursor: "pointer",
        transition: "all 0.15s ease",
      }}
    >
      {icon}
      {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// WorkforcePanel
// ---------------------------------------------------------------------------

export function WorkforcePanel({ workers }: { workers: Worker[] }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");

  const filtered = filter === "all"
    ? workers
    : workers.filter((w) => w.status === filter);

  const running = workers.filter((w) => w.status === "running" || w.status === "busy").length;
  const idle = workers.filter((w) => w.status === "idle").length;
  const totalTokens = workers.reduce((s, w) => s + w.tokensUsed, 0);
  const totalCost = workers.reduce((s, w) => s + w.cost, 0);

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "12px", height: "100%" }}>
      {/* Summary row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "8px",
        }}
      >
        <SummaryCard label="Active" value={String(running)} color="var(--green)" />
        <SummaryCard label="Idle" value={String(idle)} color="var(--text-muted)" />
        <SummaryCard label="Tokens" value={`${(totalTokens / 1000).toFixed(1)}k`} color="var(--text-secondary)" />
        <SummaryCard label="Cost" value={`$${totalCost.toFixed(2)}`} color="var(--accent)" />
      </div>

      {/* Filter pills */}
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
        {["all", "running", "busy", "idle", "offline", "error"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: "4px 10px",
              borderRadius: "9999px",
              fontSize: "0.68rem",
              fontWeight: filter === f ? 600 : 400,
              background: filter === f ? "var(--accent)" : "var(--surface)",
              color: filter === f ? "#fff" : "var(--text-secondary)",
              border: `1px solid ${filter === f ? "var(--accent)" : "var(--border)"}`,
              cursor: "pointer",
              textTransform: "capitalize",
            }}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Worker cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px", overflow: "auto" }}>
        {filtered.map((w) => (
          <WorkerCard
            key={w.id}
            worker={w}
            expanded={expandedId === w.id}
            onToggle={() => setExpandedId(expandedId === w.id ? null : w.id)}
          />
        ))}
        {filtered.length === 0 && (
          <div
            style={{
              padding: "32px",
              textAlign: "center",
              color: "var(--text-muted)",
              fontSize: "0.82rem",
            }}
          >
            No workers matching filter
          </div>
        )}
      </div>
    </div>
  );
}

function SummaryCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div
      style={{
        padding: "10px 12px",
        borderRadius: "var(--radius-md)",
        background: "var(--bg-subtle)",
        border: "1px solid var(--border)",
      }}
    >
      <div style={{ fontSize: "0.62rem", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px" }}>
        {label}
      </div>
      <div style={{ fontSize: "1.1rem", fontWeight: 700, color, fontFamily: "var(--font-mono)" }}>
        {value}
      </div>
    </div>
  );
}
