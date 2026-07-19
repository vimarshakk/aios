"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { cn } from "@/lib/cn";
import { api, type GoalSnapshot } from "@/lib/api";
import {
  Target, Plus, ChevronDown, ChevronRight, CheckCircle2,
  Circle, Clock, AlertCircle, MoreHorizontal, Filter, Search,
  Pause, Play, XCircle, Loader2,
} from "lucide-react";

type GoalStatus = "planning" | "in_progress" | "completed" | "failed" | "paused" | "cancelled";

const GOAL_STATUS_UI: Record<string, { icon: React.ComponentType<{ size?: number }>; color: string; label: string }> = {
  planning: { icon: Clock, color: "var(--yellow)", label: "Planning" },
  in_progress: { icon: Loader2, color: "var(--accent)", label: "In Progress" },
  completed: { icon: CheckCircle2, color: "var(--green)", label: "Completed" },
  failed: { icon: Circle, color: "var(--red)", label: "Failed" },
  paused: { icon: AlertCircle, color: "var(--yellow)", label: "Paused" },
  cancelled: { icon: XCircle, color: "var(--text-muted)", label: "Cancelled" },
};

interface GoalUI {
  id: string;
  title: string;
  description: string;
  status: GoalStatus;
  progress: number;
  steps: { id: string; title: string; done: boolean }[];
  createdAt: string;
  elapsed: string;
}

function mapGoal(snap: GoalSnapshot): GoalUI {
  const status = (snap.status ?? "planning") as GoalStatus;
  const steps = (snap.steps ?? []).map((s, i) => ({
    id: s.id ?? `step-${i}`,
    title: s.name ?? s.id ?? `Step ${i + 1}`,
    done: s.status === "completed",
  }));
  const completedSteps = steps.filter((s) => s.done).length;
  const progress = steps.length > 0 ? Math.round((completedSteps / steps.length) * 100) : 0;

  let elapsed = "";
  const elapsedMs = snap.elapsed_ms as number | undefined;
  if (elapsedMs != null && typeof elapsedMs === "number") {
    const secs = Math.round(elapsedMs / 1000);
    elapsed = secs >= 60 ? `${Math.floor(secs / 60)}m ${secs % 60}s` : `${secs}s`;
  }

  return {
    id: snap.goal_id,
    title: snap.objective ?? "Untitled Goal",
    description: snap.error ? `Error: ${snap.error}` : "",
    status,
    progress,
    steps,
    createdAt: String(snap.started_at ?? ""),
    elapsed,
  };
}

function formatTime(iso: string): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

export function GoalsWorkspace() {
  const [goals, setGoals] = useState<GoalUI[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const unsubRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.listGoals().then((snapshots) => {
      if (cancelled) return;
      const mapped = snapshots.map(mapGoal);
      setGoals(mapped);
      setLoading(false);
      if (mapped.length > 0 && !expandedId) {
        setExpandedId(mapped.find((g) => g.status === "in_progress" || g.status === "planning")?.id ?? mapped[0].id);
      }
    }).catch(() => setLoading(false));

    unsubRef.current = api.subscribeAllGoals(
      (snapshots) => {
        if (cancelled) return;
        const mapped = snapshots.map(mapGoal);
        setGoals(mapped);
      },
      () => {},
      () => {},
    );

    return () => { cancelled = true; unsubRef.current?.(); };
  }, []);

  const filtered = goals.filter((g) => {
    if (filter !== "all" && g.status !== filter) return false;
    if (searchQuery && !g.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const toggleExpand = (id: string) => setExpandedId((prev) => (prev === id ? null : id));

  const handlePause = useCallback((id: string) => { api.pauseGoal(id).catch(() => {}); }, []);
  const handleResume = useCallback((id: string) => { api.resumeGoal(id).catch(() => {}); }, []);
  const handleCancel = useCallback((id: string) => { api.cancelGoal(id).catch(() => {}); }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-6 py-3 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex-1" />
        <div className="flex items-center gap-2">
          {(["all", "planning", "in_progress", "completed", "failed", "paused", "cancelled"] as const).map((f) => (
            <button
              key={f}
              className={cn("goals-filter-btn", filter === f && "active")}
              onClick={() => setFilter(f)}
            >
              {f === "all" ? "All" : (GOAL_STATUS_UI[f]?.label ?? f)}
            </button>
          ))}
        </div>
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search goals…"
            className="goals-search"
          />
        </div>
      </div>

      {/* Goal list */}
      <div className="flex-1 overflow-y-auto p-6 space-y-3">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-40 gap-3">
            <span style={{ color: "var(--text-muted)" }}><Loader2 size={28} className="animate-spin" /></span>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Loading goals…</p>
          </div>
        ) : filtered.map((goal) => {
          const isExpanded = expandedId === goal.id;
          const statusCfg = GOAL_STATUS_UI[goal.status] ?? GOAL_STATUS_UI.planning;
          const StatusIcon = statusCfg.icon;
          const isRunning = goal.status === "in_progress" || goal.status === "planning";
          const isPaused = goal.status === "paused";

          return (
            <div key={goal.id} className="goals-card">
              {/* Goal header */}
              <button className="goals-card-header" onClick={() => toggleExpand(goal.id)}>
                <span className="goals-expand-icon">
                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </span>
                <div className="flex-1 min-w-0">
                  <span className="goals-card-title">{goal.title}</span>
                  {goal.description && <span className="goals-card-desc">{goal.description}</span>}
                </div>
                {goal.elapsed && (
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>{goal.elapsed}</span>
                )}
                <span className="goals-progress-badge" style={{ color: statusCfg.color }}>
                  {goal.progress}%
                </span>
                <span style={{ color: statusCfg.color }}><StatusIcon size={16} /></span>
                {/* Action buttons */}
                <div className="flex items-center gap-1 ml-2" onClick={(e) => e.stopPropagation()}>
                  {isRunning && (
                    <button className="btn-icon" style={{ border: "none" }} onClick={() => handlePause(goal.id)} title="Pause">
                      <Pause size={14} />
                    </button>
                  )}
                  {isPaused && (
                    <button className="btn-icon" style={{ border: "none" }} onClick={() => handleResume(goal.id)} title="Resume">
                      <Play size={14} />
                    </button>
                  )}
                  {(isRunning || isPaused) && (
                    <button className="btn-icon" style={{ border: "none" }} onClick={() => handleCancel(goal.id)} title="Cancel">
                      <XCircle size={14} />
                    </button>
                  )}
                </div>
              </button>

              {/* Expanded content */}
              {isExpanded && (
                <div className="goals-card-body">
                  <div className="goals-progress-track">
                    <div className="goals-progress-fill" style={{ width: `${goal.progress}%`, background: statusCfg.color }} />
                  </div>
                  {goal.steps.length > 0 && (
                    <div className="space-y-1.5">
                      {goal.steps.map((step) => (
                        <div key={step.id} className="goals-subtask">
                          {step.done ? (
                            <span style={{ color: "var(--green)" }}><CheckCircle2 size={14} /></span>
                          ) : (
                            <span style={{ color: "var(--text-muted)" }}><Circle size={14} /></span>
                          )}
                          <span
                            className={cn("text-sm", step.done && "line-through")}
                            style={{ color: step.done ? "var(--text-muted)" : "var(--text-primary)" }}
                          >
                            {step.title}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="goals-meta">
                    {goal.createdAt && <span>Started {formatTime(goal.createdAt)}</span>}
                    <span>Status: {statusCfg.label}</span>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {!loading && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 gap-3 text-center">
            <span style={{ color: "var(--text-muted)" }}><Target size={28} /></span>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              {searchQuery ? "No goals match your search" : "No goals yet. Start one from the Command Bar."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
