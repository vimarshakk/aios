"use client";

import { Mic, Cpu, HardDrive, Globe, Wifi, WifiOff } from "lucide-react";
import { StatusBadge } from "../components/shared/StatusBadge";

interface StatusBarProps {
  online?: boolean;
}

export function StatusBar({ online = true }: StatusBarProps) {
  return (
    <div
      style={{
        height: 32,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 16px",
        background: "var(--bg-subtle)",
        borderTop: "1px solid var(--border)",
        fontSize: "0.65rem",
        color: "var(--text-muted)",
        flexShrink: 0,
        gap: "16px",
      }}
    >
      {/* Left: Voice + Providers */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <button
          style={{
            display: "flex",
            alignItems: "center",
            gap: "5px",
            padding: "2px 8px",
            borderRadius: "9999px",
            background: "rgba(224,94,56,0.1)",
            border: "1px solid rgba(224,94,56,0.2)",
            color: "var(--accent)",
            fontSize: "0.65rem",
            cursor: "pointer",
          }}
        >
          <Mic size={11} />
          <span>Voice</span>
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <StatusBadge label="Claude" status="active" size="sm" />
          <StatusBadge label="Gemini" status="active" size="sm" />
          <StatusBadge label="Ollama" status="idle" size="sm" />
        </div>
      </div>

      {/* Right: System */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          {online ? <Wifi size={11} /> : <WifiOff size={11} />}
          <span>{online ? "Online" : "Offline"}</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <Globe size={11} />
          <span>Gateway</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <Cpu size={11} />
          <span>--</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <HardDrive size={11} />
          <span>--</span>
        </div>
      </div>
    </div>
  );
}
