"use client";

import { useState, useEffect } from "react";
import { api, type AgentInfo } from "@/lib/api";
import {
  Users, Plus, Search, Bot, Shield, Settings, MoreHorizontal,
  Power, PowerOff, Loader2,
} from "lucide-react";

interface AgentUI {
  id: string;
  name: string;
  role: string;
  description: string;
  model: string;
  status: "active" | "inactive";
  permissions: string[];
}

export function AgentsWorkspace() {
  const [agents, setAgents] = useState<AgentUI[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    api.agents().then((data: AgentInfo[]) => {
      const mapped: AgentUI[] = data.map((a) => ({
        id: a.name ?? String(Math.random()),
        name: a.name ?? "Agent",
        role: a.type ?? "General",
        description: a.description ?? "",
        model: a.model ?? "qwen3:latest",
        status: "active" as const,
        permissions: a.capabilities ?? ["read"],
      }));
      setAgents(mapped);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const filtered = agents.filter((a) =>
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.role.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const selected = agents.find((a) => a.id === selectedId);

  return (
    <div className="flex h-full">
      {/* Agent list */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="flex items-center gap-3 px-6 py-3 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex-1" />
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search agents…"
              className="agents-search"
            />
          </div>
        </div>

        {/* Agent cards */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-40 gap-3">
              <span style={{ color: "var(--text-muted)" }}><Loader2 size={28} className="animate-spin" /></span>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>Loading agents…</p>
            </div>
          ) : filtered.map((agent) => {
            const isActive = agent.status === "active";
            return (
              <div
                key={agent.id}
                className={`agents-card ${selectedId === agent.id ? "selected" : ""}`}
                onClick={() => setSelectedId(agent.id)}
              >
                <div className="agents-card-icon">
                  <Bot size={20} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="agents-card-title">{agent.name}</span>
                    <span className="agents-role-badge">{agent.role}</span>
                    <span className={`agents-status-dot ${isActive ? "active" : ""}`} />
                  </div>
                  {agent.description && <span className="agents-card-desc">{agent.description}</span>}
                  <div className="agents-permissions">
                    {agent.permissions.map((p) => (
                      <span key={p} className="agents-perm-badge">{p}</span>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}

          {!loading && filtered.length === 0 && (
            <div className="flex flex-col items-center justify-center h-40 gap-3 text-center">
              <span style={{ color: "var(--text-muted)" }}><Users size={28} /></span>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                {searchQuery ? "No agents match your search" : "No agents registered."}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Agent config panel */}
      {selected && (
        <div
          className="w-72 shrink-0 overflow-y-auto p-4"
          style={{ borderLeft: "1px solid var(--border)", background: "var(--bg-subtle)" }}
        >
          <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
            {selected.name}
          </h3>
          <div className="space-y-3">
            <div>
              <label className="settings-label">Role</label>
              <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>{selected.role}</p>
            </div>
            <div>
              <label className="settings-label">Model</label>
              <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>{selected.model}</p>
            </div>
            <div>
              <label className="settings-label">Permissions</label>
              <div className="flex flex-wrap gap-1 mt-1">
                {selected.permissions.map((p) => (
                  <span key={p} className="agents-perm-badge">{p}</span>
                ))}
              </div>
            </div>
            {selected.description && (
              <div>
                <label className="settings-label">Description</label>
                <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>{selected.description}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
