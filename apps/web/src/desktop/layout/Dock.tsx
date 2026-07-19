"use client";

import { useWorkspaceStore } from "../state/workspace";
import { useLayoutStore } from "../state/layout";
import { getWorkspacesForMode } from "../workspaces/registry";
import {
  Home, Target, MessageSquare, Brain, FolderKanban, Users,
  Wrench, ScrollText, Settings, Zap, LayoutDashboard,
  ChevronLeft, ChevronRight,
} from "lucide-react";

const ICON_MAP: Record<string, typeof Home> = {
  Home, Target, MessageSquare, Brain, FolderKanban, Users,
  Wrench, ScrollText, Settings, Zap, LayoutDashboard,
};

export function Dock() {
  const { activeId, setActive } = useWorkspaceStore();
  const { appMode, dock, toggleDock } = useLayoutStore();
  const workspaces = getWorkspacesForMode(appMode);

  return (
    <div
      style={{
        width: dock.collapsed ? 48 : dock.width,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        background: "var(--bg-subtle)",
        borderRight: "1px solid var(--border)",
        padding: "8px 0",
        gap: "2px",
        transition: "width 0.2s ease",
        flexShrink: 0,
        overflow: "hidden",
      }}
    >
      {/* App icon */}
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: "var(--radius-md)",
          background: "linear-gradient(135deg, var(--accent), var(--accent-hover))",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: "12px",
          flexShrink: 0,
        }}
      >
        <span style={{ fontSize: "0.85rem", fontWeight: 800, color: "#fff" }}>A</span>
      </div>

      {/* Workspace icons */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "2px", overflow: "auto", width: "100%", padding: "0 6px" }}>
        {workspaces.map((ws) => {
          const Icon = ICON_MAP[ws.icon] || Home;
          const active = activeId === ws.id;
          return (
            <button
              key={ws.id}
              onClick={() => setActive(ws.id)}
              title={ws.title}
              style={{
                width: "100%",
                height: 40,
                display: "flex",
                alignItems: "center",
                justifyContent: dock.collapsed ? "center" : "flex-start",
                gap: "10px",
                padding: dock.collapsed ? "0" : "0 10px",
                borderRadius: "var(--radius-md)",
                background: active ? "var(--surface-active)" : "transparent",
                border: "none",
                color: active ? "var(--text-primary)" : "var(--text-secondary)",
                cursor: "pointer",
                transition: "all 0.15s ease",
                flexShrink: 0,
              }}
              onMouseEnter={(e) => {
                if (!active) e.currentTarget.style.background = "var(--surface-hover)";
              }}
              onMouseLeave={(e) => {
                if (!active) e.currentTarget.style.background = "transparent";
              }}
            >
              <Icon size={18} style={{ flexShrink: 0 }} />
              {!dock.collapsed && (
                <span style={{ fontSize: "0.75rem", fontWeight: active ? 600 : 400, whiteSpace: "nowrap" }}>
                  {ws.title}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Collapse toggle */}
      <button
        onClick={toggleDock}
        style={{
          width: 28,
          height: 28,
          borderRadius: "var(--radius-sm)",
          background: "transparent",
          border: "1px solid var(--border)",
          color: "var(--text-muted)",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginTop: "8px",
          flexShrink: 0,
        }}
      >
        {dock.collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
    </div>
  );
}
