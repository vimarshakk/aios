"use client";

import { useState } from "react";
import type { ReviewRequest } from "../../types";
import {
  Eye, CheckCircle2, XCircle, Clock, AlertTriangle,
  ChevronDown, ChevronRight, MessageSquare, ArrowRight,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Status config
// ---------------------------------------------------------------------------

const REVIEW_STATUS: Record<string, { icon: React.ComponentType<{ size?: number }>; color: string; bg: string; label: string }> = {
  pending: { icon: Clock, color: "#f59e0b", bg: "rgba(245, 158, 11, 0.1)", label: "Pending" },
  running: { icon: Eye, color: "#8b5cf6", bg: "rgba(139, 92, 246, 0.1)", label: "Reviewing" },
  approved: { icon: CheckCircle2, color: "var(--green)", bg: "rgba(16, 185, 129, 0.1)", label: "Approved" },
  changes_requested: { icon: AlertTriangle, color: "#f59e0b", bg: "rgba(245, 158, 11, 0.1)", label: "Changes Requested" },
  rejected: { icon: XCircle, color: "#ef4444", bg: "rgba(239, 68, 68, 0.1)", label: "Rejected" },
};

// ---------------------------------------------------------------------------
// Review card
// ---------------------------------------------------------------------------

function ReviewCard({ review }: { review: ReviewRequest }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = REVIEW_STATUS[review.status] ?? REVIEW_STATUS.pending;
  const Icon = cfg.icon;

  const elapsed = review.completedAt
    ? Math.round((review.completedAt - review.createdAt) / 1000)
    : Math.round((Date.now() - review.createdAt) / 1000);

  return (
    <div
      style={{
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border)",
        background: "var(--bg-subtle)",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
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
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: "50%",
            background: cfg.bg,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <span style={{ color: cfg.color, display: "inline-flex" }}>
            <Icon size={14} />
          </span>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>
            {review.taskName}
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            {review.sourceWorker}
            <span style={{ display: "inline", margin: "0 4px", verticalAlign: "middle", color: "var(--text-muted)" }}>
              <ArrowRight size={10} />
            </span>
            {review.reviewWorker}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
          <span
            style={{
              padding: "2px 8px",
              borderRadius: "9999px",
              fontSize: "0.65rem",
              fontWeight: 600,
              background: cfg.bg,
              color: cfg.color,
            }}
          >
            {cfg.label}
          </span>
          <span style={{ fontSize: "0.65rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            {elapsed}s
          </span>
          {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </div>
      </button>

      {/* Expanded */}
      {expanded && (
        <div style={{ padding: "0 12px 12px", borderTop: "1px solid var(--border)" }}>
          {/* Source output */}
          <div style={{ marginTop: "10px" }}>
            <div style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px" }}>
              Source Output
            </div>
            <pre
              style={{
                padding: "8px",
                borderRadius: "var(--radius-sm)",
                background: "#0a0a0a",
                color: "#d4d4d4",
                fontFamily: "var(--font-mono)",
                fontSize: "0.7rem",
                lineHeight: 1.5,
                overflow: "auto",
                maxHeight: 120,
                margin: 0,
              }}
            >
              {review.sourceOutput}
            </pre>
          </div>

          {/* Review notes */}
          {review.reviewNotes && (
            <div style={{ marginTop: "10px" }}>
              <div style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px", display: "flex", alignItems: "center", gap: "4px" }}>
                <MessageSquare size={10} />
                Review Notes
              </div>
              <div
                style={{
                  padding: "8px",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  fontSize: "0.75rem",
                  color: "var(--text-secondary)",
                  lineHeight: 1.5,
                }}
              >
                {review.reviewNotes}
              </div>
            </div>
          )}

          {/* Actions */}
          {review.status === "pending" && (
            <div style={{ display: "flex", gap: "6px", marginTop: "10px" }}>
              <button
                style={{
                  padding: "5px 12px",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.72rem",
                  fontWeight: 600,
                  background: "var(--green)",
                  color: "#fff",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Approve
              </button>
              <button
                style={{
                  padding: "5px 12px",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.72rem",
                  fontWeight: 600,
                  background: "rgba(245, 158, 11, 0.15)",
                  color: "#f59e0b",
                  border: "1px solid rgba(245, 158, 11, 0.3)",
                  cursor: "pointer",
                }}
              >
                Request Changes
              </button>
              <button
                style={{
                  padding: "5px 12px",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.72rem",
                  fontWeight: 600,
                  background: "rgba(239, 68, 68, 0.1)",
                  color: "#ef4444",
                  border: "1px solid rgba(239, 68, 68, 0.2)",
                  cursor: "pointer",
                }}
              >
                Reject
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ReviewPanel
// ---------------------------------------------------------------------------

export function ReviewPanel({ reviews }: { reviews: ReviewRequest[] }) {
  const [filter, setFilter] = useState<string>("all");

  const filtered = filter === "all"
    ? reviews
    : reviews.filter((r) => r.status === filter);

  const approved = reviews.filter((r) => r.status === "approved").length;
  const pending = reviews.filter((r) => r.status === "pending" || r.status === "running").length;

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "12px", height: "100%" }}>
      {/* Summary */}
      <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
        <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>
          AI Review Pipeline
        </span>
        <span style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}>
          {approved} approved, {pending} pending
        </span>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: "6px" }}>
        {["all", "pending", "running", "approved", "changes_requested", "rejected"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: "3px 8px",
              borderRadius: "9999px",
              fontSize: "0.65rem",
              fontWeight: filter === f ? 600 : 400,
              background: filter === f ? "var(--accent)" : "var(--surface)",
              color: filter === f ? "#fff" : "var(--text-secondary)",
              border: `1px solid ${filter === f ? "var(--accent)" : "var(--border)"}`,
              cursor: "pointer",
              textTransform: "capitalize",
            }}
          >
            {f.replace("_", " ")}
          </button>
        ))}
      </div>

      {/* Review cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px", overflow: "auto" }}>
        {filtered.map((r) => (
          <ReviewCard key={r.id} review={r} />
        ))}
        {filtered.length === 0 && (
          <div style={{ padding: "32px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.82rem" }}>
            No reviews matching filter.
          </div>
        )}
      </div>
    </div>
  );
}
