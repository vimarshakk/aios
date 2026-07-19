"use client";

import { useLayoutStore } from "../state/layout";
import { GlassCard } from "../components/shared/GlassCard";
import { SectionHeader } from "../components/shared/SectionHeader";
import { StatusBadge } from "../components/shared/StatusBadge";
import { ProgressCard } from "../components/shared/ProgressCard";
import { Brain, Terminal, Cpu, Activity, X } from "lucide-react";

const INSPECTOR_TABS = [
  { id: "ai-core", label: "AI Core", icon: Brain },
  { id: "activity", label: "Activity", icon: Activity },
  { id: "logs", label: "Logs", icon: Terminal },
];

// Mock AI Core data
const MOCK_AGENTS = [
  { name: "Planner", status: "active" as const, detail: "Creating execution graph..." },
  { name: "Executor", status: "active" as const, detail: "Writing backend API..." },
  { name: "Browser", status: "idle" as const, detail: "Searching docs..." },
  { name: "Memory", status: "active" as const, detail: "Saving architecture decision..." },
  { name: "Voice", status: "idle" as const, detail: "Listening..." },
];

const MOCK_MODELS = [
  { name: "Claude 4 Sonnet", provider: "Anthropic", status: "active" as const },
  { name: "Gemini 2.5 Pro", provider: "Google", status: "active" as const },
  { name: "Ollama Llama3", provider: "Local", status: "idle" as const },
];

function AICoreTab() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <div>
        <SectionHeader title="Agents" subtitle="Live status" />
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {MOCK_AGENTS.map((agent) => (
            <div
              key={agent.name}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "8px 12px",
                borderRadius: "var(--radius-md)",
                background: "var(--surface)",
                border: "1px solid var(--border)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <StatusBadge label={agent.name} status={agent.status} />
              </div>
              <span style={{ fontSize: "0.62rem", color: "var(--text-muted)", maxWidth: "140px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {agent.detail}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <SectionHeader title="Models" subtitle="Connected" />
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          {MOCK_MODELS.map((model) => (
            <div
              key={model.name}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "6px 12px",
                borderRadius: "var(--radius-sm)",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span style={{ fontSize: "0.7rem", color: "var(--text-primary)" }}>{model.name}</span>
                <span style={{ fontSize: "0.6rem", color: "var(--text-muted)" }}>{model.provider}</span>
              </div>
              <StatusBadge label={model.status === "active" ? "Online" : "Idle"} status={model.status} size="sm" />
            </div>
          ))}
        </div>
      </div>

      <div>
        <SectionHeader title="Execution" subtitle="Current goal" />
        <ProgressCard label="Build AIOS Desktop" progress={72} status="running" detail="Writing backend API..." />
      </div>
    </div>
  );
}

function ActivityTab() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <SectionHeader title="Live Activity" />
      {MOCK_AGENTS.filter(a => a.status === "active").map((agent) => (
        <GlassCard key={agent.name} padding="10px 12px">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <StatusBadge label={agent.name} status="active" />
          </div>
          <p style={{ fontSize: "0.68rem", color: "var(--text-secondary)", margin: "6px 0 0" }}>{agent.detail}</p>
        </GlassCard>
      ))}
    </div>
  );
}

function LogsTab() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      <SectionHeader title="Recent Logs" />
      <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.62rem", color: "var(--text-muted)", lineHeight: 1.6 }}>
        <div>[22:03] Supervisor started goal</div>
        <div>[22:05] Planner created execution graph</div>
        <div>[22:06] Claude generated API</div>
        <div>[22:07] Tests running</div>
        <div>[22:08] Memory updated</div>
      </div>
    </div>
  );
}

export function Inspector() {
  const { inspector, inspectorTab, setInspectorTab, toggleInspector } = useLayoutStore();

  if (inspector.collapsed) return null;

  return (
    <div
      style={{
        width: inspector.width,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        background: "var(--bg-subtle)",
        borderLeft: "1px solid var(--border)",
        flexShrink: 0,
        overflow: "hidden",
      }}
    >
      {/* Tab bar */}
      <div style={{ display: "flex", alignItems: "center", borderBottom: "1px solid var(--border)", padding: "0 8px" }}>
        {INSPECTOR_TABS.map((tab) => {
          const Icon = tab.icon;
          const active = inspectorTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setInspectorTab(tab.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "5px",
                padding: "10px 12px",
                fontSize: "0.68rem",
                fontWeight: active ? 600 : 400,
                color: active ? "var(--text-primary)" : "var(--text-muted)",
                background: "none",
                border: "none",
                borderBottom: active ? "2px solid var(--accent)" : "2px solid transparent",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              <Icon size={13} />
              {tab.label}
            </button>
          );
        })}
        <div style={{ flex: 1 }} />
        <button
          onClick={toggleInspector}
          style={{
            width: 24, height: 24, borderRadius: "var(--radius-sm)",
            background: "transparent", border: "none", color: "var(--text-muted)",
            cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
          }}
        >
          <X size={14} />
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: "auto", padding: "16px" }}>
        {inspectorTab === "ai-core" && <AICoreTab />}
        {inspectorTab === "activity" && <ActivityTab />}
        {inspectorTab === "logs" && <LogsTab />}
      </div>
    </div>
  );
}
