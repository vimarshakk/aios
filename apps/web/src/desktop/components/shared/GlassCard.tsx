"use client";

import type { ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  padding?: string;
  hover?: boolean;
  onClick?: () => void;
}

export function GlassCard({ children, className = "", padding = "16px", hover = false, onClick }: GlassCardProps) {
  return (
    <div
      onClick={onClick}
      className={className}
      style={{
        background: "var(--glass-bg)",
        backdropFilter: "blur(var(--glass-blur))",
        WebkitBackdropFilter: "blur(var(--glass-blur))",
        border: "1px solid var(--glass-border)",
        borderRadius: "var(--radius-lg)",
        padding,
        transition: hover ? "all 0.2s ease" : undefined,
        cursor: onClick ? "pointer" : undefined,
      }}
      onMouseEnter={hover ? (e) => {
        const el = e.currentTarget;
        el.style.borderColor = "var(--border-strong)";
        el.style.boxShadow = "var(--shadow-md)";
      } : undefined}
      onMouseLeave={hover ? (e) => {
        const el = e.currentTarget;
        el.style.borderColor = "var(--glass-border)";
        el.style.boxShadow = "none";
      } : undefined}
    >
      {children}
    </div>
  );
}
