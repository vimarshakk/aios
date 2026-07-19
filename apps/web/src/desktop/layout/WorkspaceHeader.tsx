"use client";

import { useLayoutStore, useWorkspaceStore, useSessionStore } from "../state";
import { getWorkspace } from "../workspaces/registry";
import {
  PanelRightOpen, PanelRightClose, Globe, Brain, ChevronDown,
  LayoutDashboard, Code2,
} from "lucide-react";
import { useState } from "react";

export function WorkspaceHeader() {
  const { activeId } = useWorkspaceStore();
  const { inspector, toggleInspector, appMode } = useLayoutStore();
  const { currentProject } = useSessionStore();
  const ws = getWorkspace(activeId);
  const Icon = ws?.icon;
  const [showContext, setShowContext] = useState(false);

  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 16px",
        height: 48,
        flexShrink: 0,
        borderBottom: "1px solid var(--border)",
        background: "var(--bg)",
        zIndex: "var(--z-header)",
      }}
    >
      {/* Left: workspace title + mode badge */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        {Icon && (
          <span style={{ color: "var(--accent)", display: "inline-flex" }}>
            <Icon size={18} />
          </span>
        )}
        <h1 style={{ fontSize: "0.88rem", fontWeight: 600, color: "var(--text-primary)" }}>
          {ws?.title ?? "AIOS"}
        </h1>

        {/* Mode badge */}
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            padding: "2px 8px",
            borderRadius: "var(--radius-sm)",
            background: appMode === "developer" ? "rgba(139,92,246,0.12)" : "var(--surface)",
            border: `1px solid ${appMode === "developer" ? "rgba(139,92,246,0.2)" : "var(--border)"}`,
            color: appMode === "developer" ? "#a78bfa" : "var(--text-muted)",
            fontSize: "0.62rem",
            fontWeight: 600,
            textTransform: "uppercase" as const,
            letterSpacing: "0.05em",
          }}
        >
          {appMode === "developer" ? <Code2 size={10} /> : <LayoutDashboard size={10} />}
          {appMode}
        </span>

        {/* Project context */}
        <button
          style={{
            display: "flex",
            alignItems: "center",
            gap: "5px",
            padding: "3px 8px",
            borderRadius: "var(--radius-sm)",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            color: "var(--text-secondary)",
            fontSize: "0.7rem",
            cursor: "pointer",
          }}
          onClick={() => setShowContext(!showContext)}
        >
          <Globe size={11} />
          <span style={{ maxWidth: 100, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {currentProject ?? "No project"}
          </span>
          <ChevronDown size={9} />
        </button>
      </div>

      {/* Right: inspector toggle */}
      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <button
          onClick={toggleInspector}
          style={{
            width: 28,
            height: 28,
            borderRadius: "var(--radius-sm)",
            background: "transparent",
            border: "none",
            color: inspector.collapsed ? "var(--text-muted)" : "var(--accent)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          title={inspector.collapsed ? "Show Inspector" : "Hide Inspector"}
        >
          {inspector.collapsed ? <PanelRightOpen size={16} /> : <PanelRightClose size={16} />}
        </button>
      </div>
    </header>
  );
}
