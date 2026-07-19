"use client";

import type { ReactNode } from "react";

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}

export function SectionHeader({ title, subtitle, action }: SectionHeaderProps) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
      <div>
        <h3 style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-primary)", margin: 0, letterSpacing: "0.02em" }}>
          {title}
        </h3>
        {subtitle && (
          <p style={{ fontSize: "0.68rem", color: "var(--text-muted)", margin: "2px 0 0" }}>{subtitle}</p>
        )}
      </div>
      {action}
    </div>
  );
}
