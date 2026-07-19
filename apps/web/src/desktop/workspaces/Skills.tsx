"use client";

import { useState, useEffect } from "react";
import { api, type ToolInfo } from "@/lib/api";
import {
  Wrench, Search, CheckCircle2, Circle, ExternalLink, Shield,
  Zap, FileText, Terminal, Loader2,
} from "lucide-react";

interface SkillUI {
  id: string;
  name: string;
  description: string;
  category: string;
  status: "enabled" | "disabled";
  permissions: string[];
}

const CATEGORY_ICONS: Record<string, React.ComponentType<{ size?: number }>> = {
  Automation: Zap,
  System: Terminal,
  Data: FileText,
};

export function SkillsWorkspace() {
  const [skills, setSkills] = useState<SkillUI[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCategory, setFilterCategory] = useState<string | null>(null);

  useEffect(() => {
    api.tools().then((data: ToolInfo[]) => {
      const mapped: SkillUI[] = data.map((t) => ({
        id: t.name ?? String(Math.random()),
        name: t.name ?? "Tool",
        description: t.description ?? "",
        category: t.category ?? "System",
        status: "enabled" as const,
        permissions: ["read"],
      }));
      setSkills(mapped);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const categories = [...new Set(skills.map((s) => s.category))];

  const filtered = skills.filter((s) => {
    if (filterCategory && s.category !== filterCategory) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="px-6 py-3 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-3">
          <div className="flex-1" />
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search skills…"
              className="skills-search"
            />
          </div>
        </div>
        <div className="flex items-center gap-2 mt-2">
          <button
            className={`skills-category-btn ${!filterCategory ? "active" : ""}`}
            onClick={() => setFilterCategory(null)}
          >
            All
          </button>
          {categories.map((cat) => {
            const Icon = CATEGORY_ICONS[cat] ?? Wrench;
            return (
              <button
                key={cat}
                className={`skills-category-btn ${filterCategory === cat ? "active" : ""}`}
                onClick={() => setFilterCategory(filterCategory === cat ? null : cat)}
              >
                <Icon size={12} />
                {cat}
              </button>
            );
          })}
        </div>
      </div>

      {/* Skill cards */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-40 gap-3">
            <span style={{ color: "var(--text-muted)" }}><Loader2 size={28} className="animate-spin" /></span>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Loading tools…</p>
          </div>
        ) : (
          <div className="skills-grid">
            {filtered.map((skill) => (
              <div key={skill.id} className="skills-card">
                <div className="skills-card-header">
                  <span className="skills-card-title">{skill.name}</span>
                  <span className={`skills-status-badge ${skill.status}`}>
                    {skill.status === "enabled" ? (
                      <CheckCircle2 size={12} />
                    ) : (
                      <Circle size={12} />
                    )}
                    {skill.status}
                  </span>
                </div>
                {skill.description && <p className="skills-card-desc">{skill.description}</p>}
                <div className="skills-card-footer">
                  <span className="skills-category-label">{skill.category}</span>
                  <div className="skills-perms">
                    {skill.permissions.map((p) => (
                      <span key={p} className="skills-perm-badge">{p}</span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 gap-3 text-center">
            <span style={{ color: "var(--text-muted)" }}><Wrench size={28} /></span>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              {searchQuery ? "No tools match your search" : "No tools registered."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
