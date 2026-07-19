"use client";

import { useEffect, useState } from "react";
import {
  FolderKanban, Search, RefreshCw, Clock, Folder,
} from "lucide-react";
import { api, type ProjectInfo } from "@/lib/api";

export function ProjectsWorkspace() {
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listProjects();
      setProjects(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleScan = async () => {
    try {
      setScanning(true);
      setError(null);
      const data = await api.scanProjects();
      setProjects(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setScanning(false);
    }
  };

  const filtered = projects.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.description ?? "").toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-6 py-3 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex-1" />
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search projects…"
            className="projects-search"
          />
        </div>
        <button
          className="btn-primary text-xs"
          onClick={handleScan}
          disabled={scanning}
        >
          <RefreshCw size={14} className={scanning ? "animate-spin" : ""} />
          {scanning ? "Scanning…" : "Scan"}
        </button>
      </div>

      {/* Project list */}
      <div className="flex-1 overflow-y-auto p-6 space-y-3">
        {loading && (
          <div className="flex items-center justify-center h-40" style={{ color: "var(--text-muted)" }}>
            <RefreshCw size={20} className="animate-spin mr-2" />
            Loading projects…
          </div>
        )}

        {!loading && error && (
          <div className="flex flex-col items-center justify-center h-40 gap-2 text-center">
            <p className="text-sm" style={{ color: "var(--red)" }}>
              Failed to load projects
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {error}
            </p>
            <button className="btn-primary text-xs mt-2" onClick={fetchProjects}>
              Retry
            </button>
          </div>
        )}

        {!loading && !error && filtered.map((project) => (
          <div key={project.id} className="projects-card">
            <div className="projects-card-icon">
              <Folder size={20} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="projects-card-title">{project.name}</span>
                {project.status === "active" && (
                  <span className="projects-status-badge active">Active</span>
                )}
              </div>
              <span className="projects-card-desc">{project.description}</span>
              <div className="projects-card-meta">
                <span className="flex items-center gap-1">
                  <Folder size={12} />
                  {project.path}
                </span>
                {project.last_accessed && (
                  <span className="flex items-center gap-1">
                    <Clock size={12} />
                    {project.last_accessed}
                  </span>
                )}
                {(project.languages ?? []).length > 0 && (
                  <span>{(project.languages ?? []).join(", ")}</span>
                )}
                {(project.file_count ?? 0) > 0 && (
                  <span>{(project.file_count ?? 0).toLocaleString()} files</span>
                )}
              </div>
            </div>
          </div>
        ))}

        {!loading && !error && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 gap-3 text-center">
            <span style={{ color: "var(--text-muted)" }}><FolderKanban size={28} /></span>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              {searchQuery ? "No projects match your search" : "No projects found. Click Scan to discover projects."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
