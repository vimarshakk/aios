"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { Repository } from "../types";
import {
  FolderGit2, GitBranch, FileText, Clock, Users, AlertCircle,
  ChevronRight, ExternalLink, Search,
} from "lucide-react";

const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  active: { color: "#10b981", bg: "rgba(16, 185, 129, 0.12)", label: "Active" },
  idle: { color: "var(--text-muted)", bg: "var(--surface)", label: "Idle" },
  error: { color: "#ef4444", bg: "rgba(239, 68, 68, 0.12)", label: "Error" },
  building: { color: "#f59e0b", bg: "rgba(245, 158, 11, 0.12)", label: "Building" },
};

const LANG_COLORS: Record<string, string> = {
  TypeScript: "#3178c6",
  Python: "#3776ab",
  JavaScript: "#f7df1e",
  Rust: "#dea584",
  Go: "#00add8",
};

function RepoCard({ repo, expanded, onToggle }: { repo: Repository; expanded: boolean; onToggle: () => void }) {
  const cfg = STATUS_CONFIG[repo.status] ?? STATUS_CONFIG.idle;
  const langColor = LANG_COLORS[repo.language] ?? "var(--text-muted)";

  return (
    <div style={{ borderRadius: "var(--radius-md)", border: "1px solid var(--border)", background: "var(--bg-subtle)", overflow: "hidden" }}>
      <button onClick={onToggle} style={{ display: "flex", alignItems: "center", width: "100%", padding: "12px 14px", gap: "12px", background: "none", border: "none", cursor: "pointer", textAlign: "left" }}>
        <div style={{ width: 32, height: 32, borderRadius: "var(--radius-sm)", background: `${langColor}15`, border: `1px solid ${langColor}30`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          <span style={{ color: langColor, display: "inline-flex" }}><FolderGit2 size={16} /></span>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>{repo.name}</span>
            <span style={{ padding: "1px 6px", borderRadius: "9999px", fontSize: "0.62rem", fontWeight: 600, background: cfg.bg, color: cfg.color }}>{cfg.label}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "3px", fontSize: "0.7rem", color: "var(--text-secondary)" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: "3px" }}><GitBranch size={10} />{repo.branch}</span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: "3px" }}><FileText size={10} />{repo.files} files</span>
            <span style={{ color: langColor, fontWeight: 500 }}>{repo.language}</span>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
          {repo.uncommittedChanges > 0 && (
            <span style={{ padding: "2px 6px", borderRadius: "9999px", fontSize: "0.62rem", fontWeight: 600, background: "rgba(245, 158, 11, 0.12)", color: "#f59e0b" }}>
              {repo.uncommittedChanges} changes
            </span>
          )}
          <span style={{ color: "var(--text-muted)", display: "inline-flex" }}>{expanded ? <ChevronRight size={14} style={{ transform: "rotate(90deg)" }} /> : <ChevronRight size={14} />}</span>
        </div>
      </button>

      {expanded && (
        <div style={{ padding: "0 14px 14px", borderTop: "1px solid var(--border)" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", marginTop: "10px" }}>
            <InfoCell label="Path" value={repo.path} mono />
            <InfoCell label="Last Commit" value={repo.lastCommit || "—"} />
            <InfoCell label="Assigned Workers" value={repo.workers.length > 0 ? repo.workers.join(", ") : "None"} />
          </div>
          {repo.workers.length > 0 && (
            <div style={{ display: "flex", gap: "6px", marginTop: "10px" }}>
              {repo.workers.map((w) => (
                <span key={w} style={{ padding: "3px 8px", borderRadius: "9999px", fontSize: "0.68rem", fontWeight: 500, background: "var(--surface)", color: "var(--text-secondary)", border: "1px solid var(--border)", display: "flex", alignItems: "center", gap: "4px" }}>
                  <Users size={10} />{w}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function InfoCell({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ padding: "6px 8px", borderRadius: "var(--radius-sm)", background: "var(--surface)", border: "1px solid var(--border)" }}>
      <div style={{ fontSize: "0.62rem", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "2px" }}>{label}</div>
      <div style={{ fontSize: "0.72rem", fontWeight: 500, color: "var(--text-primary)", fontFamily: mono ? "var(--font-mono)" : "inherit", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{value}</div>
    </div>
  );
}

export function RepositoriesWorkspace() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const data = await api.repositories.list();
      const mapped: Repository[] = (Array.isArray(data) ? data : []).map((r: Record<string, unknown>) => ({
        id: r.id as string,
        name: r.name as string,
        path: r.path as string,
        branch: r.branch as string,
        status: (r.status as string) as Repository["status"],
        language: r.language as string,
        files: (r.files as number) || 0,
        lastCommit: r.lastCommit as string | undefined,
        workers: (r.workers as string[]) || [],
        uncommittedChanges: (r.uncommittedChanges as number) || 0,
      }));
      setRepos(mapped);
      setLoading(false);
      setError(null);
    } catch (e) {
      setError(String(e));
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)" }}>
        <span style={{ fontSize: "0.85rem" }}>Loading repositories...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)", gap: "8px" }}>
        <span style={{ fontSize: "0.85rem" }}>Could not load repositories</span>
        <span style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>{error}</span>
        <button onClick={fetchData} style={{ marginTop: "8px", padding: "6px 14px", borderRadius: "6px", background: "var(--accent)", color: "#fff", border: "none", fontSize: "0.75rem", cursor: "pointer" }}>Retry</button>
      </div>
    );
  }

  const filtered = search
    ? repos.filter((r) => r.name.toLowerCase().includes(search.toLowerCase()) || r.language.toLowerCase().includes(search.toLowerCase()))
    : repos;

  const active = repos.filter((r) => r.status === "active").length;
  const totalFiles = repos.reduce((s, r) => s + r.files, 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", borderBottom: "1px solid var(--border)", background: "var(--bg-subtle)", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ color: "var(--accent)", display: "inline-flex" }}><FolderGit2 size={16} /></span>
          <span style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>Repositories</span>
          <span style={{ fontSize: "0.65rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", padding: "2px 6px", borderRadius: "4px", background: active > 0 ? "rgba(16, 185, 129, 0.15)" : "var(--surface)", color: active > 0 ? "var(--green)" : "var(--text-muted)" }}>
            {active}/{repos.length} active
          </span>
        </div>
        <div style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}>
          {totalFiles.toLocaleString()} files indexed
        </div>
      </div>

      {/* Search */}
      <div style={{ padding: "8px 16px", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "6px 10px", borderRadius: "var(--radius-sm)", background: "var(--surface)", border: "1px solid var(--border)" }}>
          <span style={{ color: "var(--text-muted)", display: "inline-flex" }}><Search size={14} /></span>
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search repositories..." style={{ flex: 1, background: "none", border: "none", outline: "none", color: "var(--text-primary)", fontSize: "0.78rem" }} />
        </div>
      </div>

      {/* Repo list */}
      <div style={{ flex: 1, overflow: "auto", padding: "12px 16px", display: "flex", flexDirection: "column", gap: "8px" }}>
        {filtered.map((repo) => (
          <RepoCard key={repo.id} repo={repo} expanded={expandedId === repo.id} onToggle={() => setExpandedId(expandedId === repo.id ? null : repo.id)} />
        ))}
        {filtered.length === 0 && (
          <div style={{ padding: "32px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.82rem" }}>
            No repositories found
          </div>
        )}
      </div>
    </div>
  );
}

export default RepositoriesWorkspace;
