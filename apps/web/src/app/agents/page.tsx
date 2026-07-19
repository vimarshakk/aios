"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Bot, Globe, Code2, Brain, Eye, Sparkles, Zap, ArrowLeft } from "lucide-react";
import { api, type AgentInfo } from "@/lib/api";
import Link from "next/link";

const AGENT_ICONS: Record<string, React.ReactNode> = {
  default:  <Sparkles size={22} />,
  research: <Globe size={22} />,
  coding:   <Code2 size={22} />,
  browser:  <Globe size={22} />,
  memory:   <Brain size={22} />,
  vision:   <Eye size={22} />,
};
const AGENT_COLORS: Record<string, string> = {
  default:  "#6e7cff",
  research: "#06b6d4",
  coding:   "#10b981",
  browser:  "#f59e0b",
  memory:   "#a78bfa",
  vision:   "#ec4899",
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);

  useEffect(() => { api.agents().then(setAgents).catch(console.error); }, []);

  return (
    <div style={{ minHeight: "100dvh", background: "var(--aios-bg)", padding: "32px 40px" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 32 }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--aios-text-2)", textDecoration: "none", fontSize: "0.875rem" }}>
            <ArrowLeft size={16} /> Back to Chat
          </Link>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
          <div style={{ width: 40, height: 40, borderRadius: "50%", background: "linear-gradient(135deg, #6e7cff, #a78bfa)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Zap size={18} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.03em" }}>Agent Dashboard</h1>
            <p style={{ color: "var(--aios-text-2)", fontSize: "0.85rem" }}>{agents.length} agents registered and ready</p>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
          {agents.map((agent, i) => {
            const color = AGENT_COLORS[agent.name] || "#6e7cff";
            return (
              <motion.div
                key={agent.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.07 }}
                className="glass-card"
                style={{ padding: 24, cursor: "pointer" }}
                onClick={() => window.location.href = `/?agent=${agent.name}`}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 14 }}>
                  <div style={{ width: 48, height: 48, borderRadius: "var(--r-md)", background: `${color}18`, border: `1px solid ${color}40`, display: "flex", alignItems: "center", justifyContent: "center", color }}>
                    {AGENT_ICONS[agent.name] || <Bot size={22} />}
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "1rem", textTransform: "capitalize" }}>{agent.name}</div>
                    <div style={{ fontSize: "0.72rem", color: "var(--aios-text-3)" }}>{agent.type}</div>
                  </div>
                </div>

                <p style={{ fontSize: "0.82rem", color: "var(--aios-text-2)", marginBottom: 14, lineHeight: 1.5 }}>
                  {agent.description}
                </p>

                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
                  {agent.capabilities.map((cap) => (
                    <span key={cap} style={{ fontSize: "0.65rem", padding: "2px 8px", borderRadius: "999px", background: `${color}15`, color, border: `1px solid ${color}30`, fontWeight: 600 }}>
                      {cap}
                    </span>
                  ))}
                </div>

                {agent.model && (
                  <div style={{ fontSize: "0.72rem", color: "var(--aios-text-3)", borderTop: "1px solid var(--aios-border)", paddingTop: 12 }}>
                    Model: <span style={{ color: "var(--aios-text-2)" }}>{agent.model.split("/").pop()}</span>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
