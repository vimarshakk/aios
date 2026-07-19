"use client";

import { useLayoutStore } from "../state";
import {
  Activity, Brain, Files, Wrench, ScrollText, BarChart3,
} from "lucide-react";
import type { ComponentType } from "react";

interface RightPanelTab {
  id: string;
  label: string;
  icon: ComponentType<{ size?: number }>;
}

const tabs: RightPanelTab[] = [
  { id: "execution", label: "Execution", icon: Activity },
  { id: "memory",    label: "Memory",    icon: Brain },
  { id: "files",     label: "Files",     icon: Files },
  { id: "skills",    label: "Skills",    icon: Wrench },
  { id: "logs",      label: "Logs",      icon: ScrollText },
  { id: "metrics",   label: "Metrics",   icon: BarChart3 },
];

export function RightPanel() {
  const { rightPanel, rightPanelTab, setRightPanelTab } = useLayoutStore();

  if (rightPanel.collapsed) return null;

  const active = rightPanelTab ?? "execution";

  return (
    <div
      className="h-full flex flex-col"
      style={{
        width: rightPanel.width,
        borderLeft: "1px solid var(--border)",
        background: "var(--bg-subtle)",
      }}
    >
      {/* Tab bar */}
      <div
        className="flex items-center gap-0 overflow-x-auto shrink-0"
        style={{ borderBottom: "1px solid var(--border)", padding: "0 4px" }}
      >
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = active === tab.id;
          return (
            <button
              key={tab.id}
              className="flex items-center gap-1.5 px-3 py-2.5 text-xs whitespace-nowrap transition-colors"
              style={{
                color: isActive ? "var(--accent)" : "var(--text-muted)",
                borderBottom: isActive
                  ? "2px solid var(--accent)"
                  : "2px solid transparent",
                background: "transparent",
                border: "none",
                borderBottomWidth: 2,
                borderBottomStyle: "solid",
                borderBottomColor: isActive ? "var(--accent)" : "transparent",
                cursor: "pointer",
              }}
              onClick={() => setRightPanelTab(tab.id)}
            >
              <Icon size={13} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        <RightPanelPlaceholder tab={active} />
      </div>
    </div>
  );
}

function RightPanelPlaceholder({ tab }: { tab: string }) {
  const descriptions: Record<string, string> = {
    execution: "Planning, tool execution status, and context will appear here during goal execution.",
    memory:    "Related entities, sources, and confidence scores will appear here.",
    files:     "File metadata, git diff, and AI summary will appear here.",
    skills:    "Active skills, permissions, and health status will appear here.",
    logs:      "Real-time execution logs will appear here.",
    metrics:   "Performance, latency, and resource metrics will appear here.",
  };

  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        {descriptions[tab] ?? "Panel content coming in Phase 2."}
      </p>
      <span
        className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-[0.6rem]"
        style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-muted)" }}
      >
        Phase 2
      </span>
    </div>
  );
}
