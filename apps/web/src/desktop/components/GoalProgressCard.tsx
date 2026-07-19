"use client";

import { useEffect, useRef, useState } from "react";
import { api, type GoalSnapshot, type GoalStep } from "@/lib/api";
import { Target, CheckCircle2, Loader2, XCircle, Circle, PauseCircle } from "lucide-react";

// ---------------------------------------------------------------------------
// Goal Progress Card — live planner/executor visualization, inline in chat
// ---------------------------------------------------------------------------

function stepStatusIcon(status?: string) {
  switch (status) {
    case "completed":
      return <CheckCircle2 size={13} style={{ color: "var(--success)" }} />;
    case "running":
    case "in_progress":
      return <Loader2 size={13} className="animate-spin" style={{ color: "var(--accent)" }} />;
    case "failed":
    case "error":
      return <XCircle size={13} style={{ color: "var(--danger)" }} />;
    case "waiting_approval":
    case "paused":
      return <PauseCircle size={13} style={{ color: "var(--text-muted)" }} />;
    case "pending":
    case "planned":
    default:
      return <Circle size={13} style={{ color: "var(--text-muted)" }} />;
  }
}

export function GoalProgressCard({ goalId, objective }: { goalId: string; objective: string }) {
  const [snap, setSnap] = useState<GoalSnapshot | null>(null);
  const [closed, setClosed] = useState(false);
  const unsubRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    unsubRef.current = api.subscribeGoal(
      goalId,
      (s) => setSnap(s),
      () => setClosed(true),
      () => setClosed(true),
    );
    return () => unsubRef.current?.();
  }, [goalId]);

  const status = snap?.status ?? "planning";
  const steps: GoalStep[] = snap?.steps ?? [];
  const done = closed && snap?.status && ["completed", "failed", "cancelled", "canceled"].includes(snap.status);

  return (
    <div
      className="rounded-xl px-4 py-3 my-3"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <Target size={15} style={{ color: "var(--accent)" }} />
        <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
          {objective}
        </span>
        <span
          className="ml-auto text-[0.6rem] px-1.5 py-0.5 rounded capitalize"
          style={{
            background: done ? "var(--surface-active)" : "var(--accent-glow)",
            color: done ? "var(--text-secondary)" : "var(--accent)",
          }}
        >
          {status}
        </span>
      </div>

      {/* Steps */}
      {steps.length > 0 ? (
        <div className="flex flex-col gap-1.5 pl-1">
          {steps.map((s, i) => (
            <div key={s.id ?? i} className="flex items-center gap-2">
              {stepStatusIcon(s.status)}
              <span
                className="text-xs"
                style={{
                  color:
                    s.status === "completed"
                      ? "var(--text-secondary)"
                      : s.status === "failed"
                        ? "var(--danger)"
                        : "var(--text-primary)",
                }}
              >
                {s.name ?? s.capability ?? s.id ?? `Step ${i + 1}`}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex items-center gap-2 py-1">
          <Loader2 size={13} className="animate-spin" style={{ color: "var(--accent)" }} />
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            Planning…
          </span>
        </div>
      )}
    </div>
  );
}
