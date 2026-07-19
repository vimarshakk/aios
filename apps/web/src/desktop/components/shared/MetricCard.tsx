"use client";

import type { ReactNode } from "react";
import { GlassCard } from "./GlassCard";

interface MetricCardProps {
  label: string;
  value: string | number;
  icon?: ReactNode;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  accent?: boolean;
}

export function MetricCard({ label, value, icon, trend, trendValue, accent }: MetricCardProps) {
  return (
    <GlassCard padding="14px" hover>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <p style={{ fontSize: "0.65rem", color: "var(--text-muted)", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {label}
          </p>
          <p style={{
            fontSize: "1.4rem", fontWeight: 700, margin: "4px 0 0",
            color: accent ? "var(--accent)" : "var(--text-primary)",
            fontFamily: "var(--font-mono)",
          }}>
            {value}
          </p>
        </div>
        {icon && (
          <span style={{ color: "var(--text-muted)", opacity: 0.5 }}>{icon}</span>
        )}
      </div>
      {trend && trendValue && (
        <div style={{
          display: "flex", alignItems: "center", gap: "4px", marginTop: "8px",
          fontSize: "0.65rem",
          color: trend === "up" ? "var(--success)" : trend === "down" ? "var(--danger)" : "var(--text-muted)",
        }}>
          <span>{trend === "up" ? "\u2191" : trend === "down" ? "\u2193" : "\u2192"}</span>
          <span>{trendValue}</span>
        </div>
      )}
    </GlassCard>
  );
}
