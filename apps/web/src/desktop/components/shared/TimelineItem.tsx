"use client";

import type { ReactNode } from "react";

interface TimelineItemProps {
  time: string;
  title: string;
  description?: string;
  icon?: ReactNode;
  status?: "completed" | "running" | "pending" | "error";
}

const STATUS_DOTS: Record<string, string> = {
  completed: "var(--success)",
  running: "var(--accent)",
  pending: "var(--text-muted)",
  error: "var(--danger)",
};

export function TimelineItem({ time, title, description, icon, status = "completed" }: TimelineItemProps) {
  return (
    <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
      {/* Timeline line + dot */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0, paddingTop: "2px" }}>
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: STATUS_DOTS[status],
            boxShadow: status === "running" ? `0 0 8px ${STATUS_DOTS[status]}` : undefined,
            animation: status === "running" ? "pulse-dot 2s ease-in-out infinite" : undefined,
          }}
        />
        <div style={{ width: 1, flex: 1, background: "var(--border)", marginTop: "4px" }} />
      </div>

      {/* Content */}
      <div style={{ flex: 1, paddingBottom: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {icon && <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>{icon}</span>}
          <span style={{ fontSize: "0.72rem", fontWeight: 500, color: "var(--text-primary)" }}>{title}</span>
        </div>
        {description && (
          <p style={{ fontSize: "0.68rem", color: "var(--text-secondary)", margin: "2px 0 0" }}>{description}</p>
        )}
        <span style={{ fontSize: "0.6rem", color: "var(--text-muted)", marginTop: "2px", display: "block" }}>{time}</span>
      </div>
    </div>
  );
}
