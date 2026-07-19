"use client";

import { useState } from "react";
import { GlassCard } from "../components/shared/GlassCard";
import { SectionHeader } from "../components/shared/SectionHeader";
import { StatusBadge } from "../components/shared/StatusBadge";
import { ProgressCard } from "../components/shared/ProgressCard";
import { TimelineItem } from "../components/shared/TimelineItem";
import { MetricCard } from "../components/shared/MetricCard";
import {
  Mic, Brain, Target, FolderKanban, Users, MessageSquare,
  ArrowRight, Sparkles, Zap, Clock, Layers, Settings,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_BRIEFING = {
  timeSince: "14 hours ago",
  agentsActive: 3,
  goalProgress: 72,
  goalTitle: "Build AIOS Desktop Application",
  recentCommits: 12,
  openPRs: 2,
  memorySaved: 47,
};

const MOCK_TIMELINE = [
  { time: "22:08", event: "Planner created execution graph for M17 Dev Mode", agent: "Planner", status: "running" as const },
  { time: "22:06", event: "Claude generated 13 backend API endpoints", agent: "Claude", status: "running" as const },
  { time: "22:05", event: "97 M17 tests passing — integration verified", agent: "QA", status: "completed" as const },
  { time: "22:03", event: "Goal resumed: M17 Integration Pass", agent: "System", status: "completed" as const },
  { time: "21:58", event: "Executor completed workforce adapter implementation", agent: "Executor", status: "completed" as const },
  { time: "21:45", event: "Memory saved architecture decision: workforce adapter pattern", agent: "Memory", status: "completed" as const },
];

const MOCK_GOALS = [
  { title: "M17 Integration Pass", progress: 72, status: "running" as const, detail: "Tests, APIs, frontend wiring" },
  { title: "UI Redesign Phase 0", progress: 15, status: "running" as const, detail: "Mission Control first layout" },
  { title: "M18 Production Readiness", progress: 0, status: "pending" as const, detail: "Docker, CI/CD, monitoring" },
];

const QUICK_ACTIONS = [
  { label: "New Goal", icon: Target, shortcut: "⌘G", accent: true },
  { label: "Chat", icon: MessageSquare, shortcut: "⌘1" },
  { label: "Projects", icon: FolderKanban, shortcut: "⌘2" },
  { label: "Memory", icon: Layers, shortcut: "⌘M" },
  { label: "Developer", icon: Zap, shortcut: "⌘⇧D" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MissionControl() {
  const [input, setInput] = useState("");

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <div
      style={{
        height: "100%",
        overflow: "auto",
        padding: "40px",
        display: "flex",
        flexDirection: "column",
        gap: "32px",
        maxWidth: 800,
        margin: "0 auto",
      }}
    >
      {/* Greeting */}
      <div style={{ animation: "fade-in 0.3s ease" }}>
        <h1
          style={{
            fontSize: "2rem",
            fontWeight: 700,
            color: "var(--text-primary)",
            lineHeight: 1.2,
          }}
        >
          {greeting}
        </h1>
        <p style={{ fontSize: "0.88rem", color: "var(--text-secondary)", marginTop: "6px" }}>
          AIOS is online. {MOCK_BRIEFING.agentsActive} agents active.
        </p>
      </div>

      {/* Command input */}
      <GlassCard padding="16px 20px">
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Sparkles size={16} style={{ color: "var(--accent)", flexShrink: 0 }} />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="What should we build today?"
            style={{
              flex: 1,
              background: "none",
              border: "none",
              outline: "none",
              color: "var(--text-primary)",
              fontSize: "0.92rem",
              fontFamily: "var(--font-sans)",
            }}
          />
          <button
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 14px",
              background: "var(--accent)",
              border: "none",
              borderRadius: "var(--radius-md)",
              color: "#fff",
              fontSize: "0.75rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <Mic size={13} />
            Speak
          </button>
        </div>
      </GlassCard>

      {/* Wake-up briefing */}
      <div style={{ animation: "fade-in 0.4s ease 0.1s both" }}>
        <SectionHeader title="While you were away" subtitle={MOCK_BRIEFING.timeSince} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px", marginTop: "8px" }}>
          <MetricCard label="Active Agents" value={MOCK_BRIEFING.agentsActive} icon={Brain} />
          <MetricCard label="Commits" value={MOCK_BRIEFING.recentCommits} icon={FolderKanban} />
          <MetricCard label="Memory Saved" value={MOCK_BRIEFING.memorySaved} icon={Layers} />
        </div>
      </div>

      {/* Active goals */}
      <div style={{ animation: "fade-in 0.4s ease 0.2s both" }}>
        <SectionHeader title="Active Goals" subtitle="In progress" />
        <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "8px" }}>
          {MOCK_GOALS.map((g) => (
            <ProgressCard
              key={g.title}
              label={g.title}
              progress={g.progress}
              status={g.status}
              detail={g.detail}
            />
          ))}
        </div>
      </div>

      {/* Timeline */}
      <div style={{ animation: "fade-in 0.4s ease 0.3s both" }}>
        <SectionHeader title="Recent Activity" subtitle="Live timeline" />
        <div style={{ display: "flex", flexDirection: "column", marginTop: "8px" }}>
          {MOCK_TIMELINE.map((item, i) => (
            <TimelineItem
              key={i}
              time={item.time}
              title={item.event}
              description={`${item.agent} • ${item.time}`}
              status={item.status}
            />
          ))}
        </div>
      </div>

      {/* Quick actions */}
      <div style={{ animation: "fade-in 0.4s ease 0.4s both" }}>
        <SectionHeader title="Quick Actions" />
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "8px" }}>
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.label}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "8px 14px",
                  background: action.accent ? "var(--accent-glow)" : "var(--surface)",
                  border: `1px solid ${action.accent ? "rgba(224,94,56,0.3)" : "var(--border)"}`,
                  borderRadius: "var(--radius-md)",
                  color: action.accent ? "var(--accent)" : "var(--text-secondary)",
                  fontSize: "0.78rem",
                  fontWeight: action.accent ? 600 : 400,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                <Icon size={14} />
                {action.label}
                {action.shortcut && (
                  <span style={{ fontSize: "0.6rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                    {action.shortcut}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
