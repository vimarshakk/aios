"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Brain, Database, GitBranch, Search, Download, Upload,
  Plus, Trash2, RefreshCw, Activity, Layers, Zap,
} from "lucide-react";
import { api } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Tab = "overview" | "workspaces" | "graph" | "search" | "export";

interface Stats {
  run_count: number;
  episodes_processed: number;
  entities_extracted: number;
  facts_stored: number;
  vector_docs_indexed: number;
  duration_ms: number;
  last_run_at: string;
  errors: string[];
}

// ---------------------------------------------------------------------------
// Tab button
// ---------------------------------------------------------------------------

function TabBtn({ active, icon: Icon, label, onClick }: {
  active: boolean;
  icon: React.ElementType;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md transition-colors"
      style={{
        background: active ? "var(--accent)" : "transparent",
        color: active ? "#fff" : "var(--text-secondary)",
      }}
    >
      <Icon size={13} />
      {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

function StatCard({ label, value, icon: Icon }: {
  label: string;
  value: string | number;
  icon: React.ElementType;
}) {
  return (
    <div className="flex flex-col gap-1 p-3 rounded-lg" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-1.5 text-xs" style={{ color: "var(--text-muted)" }}>
        <Icon size={12} />
        {label}
      </div>
      <span className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Overview Tab
// ---------------------------------------------------------------------------

function OverviewTab() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [consolidating, setConsolidating] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.memoryStats() as unknown as Stats;
      setStats(data);
    } catch { setStats(null); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleConsolidate = async () => {
    setConsolidating(true);
    setMsg(null);
    try {
      const r = await api.consolidateMemory() as unknown as Record<string, unknown>;
      setMsg(`Consolidated ${r.episodes_processed ?? 0} episodes in ${Number(r.duration_ms ?? 0).toFixed(0)}ms`);
      await load();
    } catch (e) {
      setMsg(`Error: ${e}`);
    } finally { setConsolidating(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-40" style={{ color: "var(--text-muted)" }}>Loading stats…</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Memory System Overview</h3>
        <button className="btn-primary text-xs flex items-center gap-1.5" onClick={handleConsolidate} disabled={consolidating}>
          <RefreshCw size={12} className={consolidating ? "animate-spin" : ""} />
          {consolidating ? "Consolidating…" : "Run Consolidation"}
        </button>
      </div>

      {msg && (
        <div className="text-xs px-3 py-2 rounded" style={{ background: "var(--surface)", color: msg.startsWith("Error") ? "var(--red)" : "var(--green)" }}>
          {msg}
        </div>
      )}

      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Runs" value={stats?.run_count ?? 0} icon={Activity} />
        <StatCard label="Episodes Processed" value={stats?.episodes_processed ?? 0} icon={Brain} />
        <StatCard label="Entities Extracted" value={stats?.entities_extracted ?? 0} icon={Layers} />
        <StatCard label="Facts Stored" value={stats?.facts_stored ?? 0} icon={Database} />
        <StatCard label="Vector Docs" value={stats?.vector_docs_indexed ?? 0} icon={Zap} />
        <StatCard label="Duration" value={`${Number(stats?.duration_ms ?? 0).toFixed(0)}ms`} icon={Activity} />
        <StatCard label="Errors" value={stats?.errors?.length ?? 0} icon={Activity} />
        <StatCard label="Last Run" value={stats?.last_run_at ? new Date(stats.last_run_at).toLocaleTimeString() : "Never"} icon={Activity} />
      </div>

      {stats?.errors && stats.errors.length > 0 && (
        <div className="p-3 rounded-lg text-xs" style={{ background: "var(--surface)", border: "1px solid var(--red)" }}>
          <p className="font-medium mb-1" style={{ color: "var(--red)" }}>Recent Errors</p>
          {stats.errors.slice(-5).map((e, i) => (
            <p key={i} style={{ color: "var(--text-secondary)" }}>{e}</p>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Workspaces Tab
// ---------------------------------------------------------------------------

function WorkspacesTab() {
  const [workspaces, setWorkspaces] = useState<string[]>([]);
  const [selectedWs, setSelectedWs] = useState<string | null>(null);
  const [wsDetail, setWsDetail] = useState<Record<string, unknown> | null>(null);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Array<{ content: string; score: number; metadata: Record<string, unknown> }>>([]);
  const [searching, setSearching] = useState(false);
  const [rememberContent, setRememberContent] = useState("");

  const loadList = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.listWorkspaces();
      setWorkspaces(data.workspaces ?? []);
    } catch { setWorkspaces([]); } finally { setLoading(false); }
  }, []);

  useEffect(() => { loadList(); }, [loadList]);

  const loadDetail = useCallback(async (wsId: string) => {
    try {
      const data = await api.getWorkspace(wsId);
      setWsDetail(data as unknown as Record<string, unknown>);
    } catch { setWsDetail(null); }
  }, []);

  useEffect(() => {
    if (selectedWs) loadDetail(selectedWs);
  }, [selectedWs, loadDetail]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await api.createWorkspace(newName.trim(), newDesc.trim());
      setNewName("");
      setNewDesc("");
      await loadList();
    } catch { /* ignore */ } finally { setCreating(false); }
  };

  const handleDelete = async (wsId: string) => {
    try {
      await api.deleteWorkspace(wsId);
      if (selectedWs === wsId) { setSelectedWs(null); setWsDetail(null); }
      await loadList();
    } catch { /* ignore */ }
  };

  const handleSearch = async () => {
    if (!selectedWs || !searchQuery.trim()) return;
    setSearching(true);
    try {
      const data = await api.workspaceSearch(selectedWs, searchQuery.trim());
      setSearchResults(data.results ?? []);
    } catch { setSearchResults([]); } finally { setSearching(false); }
  };

  const handleRemember = async () => {
    if (!selectedWs || !rememberContent.trim()) return;
    try {
      await api.workspaceRemember(selectedWs, rememberContent.trim());
      setRememberContent("");
      await loadDetail(selectedWs);
    } catch { /* ignore */ }
  };

  return (
    <div className="flex h-full">
      {/* Workspace list */}
      <div className="w-56 shrink-0 overflow-y-auto" style={{ borderRight: "1px solid var(--border)" }}>
        <div className="p-3 space-y-2" style={{ borderBottom: "1px solid var(--border)" }}>
          <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Workspace name" className="memory-search text-xs" />
          <input value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Description (optional)" className="memory-search text-xs" />
          <button className="btn-primary text-xs w-full flex items-center justify-center gap-1" onClick={handleCreate} disabled={creating || !newName.trim()}>
            <Plus size={12} /> {creating ? "Creating…" : "Create"}
          </button>
        </div>
        <div className="p-2 space-y-1">
          {loading && <div className="text-xs p-2" style={{ color: "var(--text-muted)" }}>Loading…</div>}
          {!loading && workspaces.length === 0 && <div className="text-xs p-2" style={{ color: "var(--text-muted)" }}>No workspaces</div>}
          {workspaces.map(ws => (
            <div
              key={ws}
              className="flex items-center justify-between px-2 py-1.5 rounded cursor-pointer text-xs group"
              style={{
                background: selectedWs === ws ? "var(--accent)" : "transparent",
                color: selectedWs === ws ? "#fff" : "var(--text-secondary)",
              }}
              onClick={() => setSelectedWs(ws)}
            >
              <span className="truncate">{ws}</span>
              <button
                className="opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={e => { e.stopPropagation(); handleDelete(ws); }}
                style={{ color: "var(--red)" }}
              >
                <Trash2 size={11} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Detail panel */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!selectedWs && (
          <div className="flex items-center justify-center h-full text-xs" style={{ color: "var(--text-muted)" }}>
            Select a workspace or create a new one
          </div>
        )}

        {selectedWs && wsDetail && (
          <>
            <div>
              <h3 className="text-sm font-semibold mb-2" style={{ color: "var(--text-primary)" }}>
                {typeof wsDetail.name === "string" ? wsDetail.name : selectedWs}
              </h3>
              {typeof wsDetail.description === "string" && wsDetail.description && <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>{wsDetail.description}</p>}
              <div className="grid grid-cols-3 gap-2">
                <StatCard label="Episodes" value={Number(wsDetail.episodes ?? 0)} icon={Brain} />
                <StatCard label="Entities" value={Number(wsDetail.entities ?? 0)} icon={Layers} />
                <StatCard label="Facts" value={Number(wsDetail.facts ?? 0)} icon={Database} />
                <StatCard label="Graph Nodes" value={Number(wsDetail.graph_nodes ?? 0)} icon={GitBranch} />
                <StatCard label="Graph Edges" value={Number(wsDetail.graph_edges ?? 0)} icon={GitBranch} />
                <StatCard label="Vector Docs" value={Number(wsDetail.vector_docs ?? 0)} icon={Zap} />
              </div>
            </div>

            {/* Add memory */}
            <div className="flex gap-2">
              <input
                value={rememberContent}
                onChange={e => setRememberContent(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleRemember()}
                placeholder="Add memory to workspace…"
                className="memory-search text-xs flex-1"
              />
              <button className="btn-primary text-xs" onClick={handleRemember} disabled={!rememberContent.trim()}>Add</button>
            </div>

            {/* Search within workspace */}
            <div className="flex gap-2">
              <input
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSearch()}
                placeholder="Search workspace…"
                className="memory-search text-xs flex-1"
              />
              <button className="btn-primary text-xs" onClick={handleSearch} disabled={searching || !searchQuery.trim()}>
                {searching ? "…" : "Search"}
              </button>
            </div>

            {searchResults.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>Search Results ({searchResults.length})</p>
                {searchResults.map((r, i) => (
                  <div key={i} className="p-2 rounded text-xs" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
                    <p style={{ color: "var(--text-primary)" }}>{r.content}</p>
                    <p className="mt-1" style={{ color: "var(--text-muted)" }}>Score: {r.score.toFixed(3)}</p>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Graph Tab
// ---------------------------------------------------------------------------

function GraphTab() {
  const [nodes, setNodes] = useState<Array<{ id: string; label: string; node_type: string; properties: Record<string, unknown> }>>([]);
  const [edges, setEdges] = useState<Array<{ id: string; source_id: string; target_id: string; relation: string; weight: number; properties: Record<string, unknown> }>>([]);
  const [components, setComponents] = useState<Array<{ size: number; representative: string }>>([]);
  const [typeFilter, setTypeFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState<"nodes" | "edges" | "components">("nodes");
  const [pathSource, setPathSource] = useState("");
  const [pathTarget, setPathTarget] = useState("");
  const [pathResult, setPathResult] = useState<{ path: string[] | null; length: number } | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [nRes, eRes, cRes] = await Promise.all([
        api.graphNodes(typeFilter || undefined, 100),
        api.graphEdges(undefined, 100),
        api.graphComponents(),
      ]);
      setNodes(nRes.nodes ?? []);
      setEdges(eRes.edges ?? []);
      setComponents((cRes.components as unknown as Array<{ size: number; representative: string }>) ?? []);
    } catch { /* ignore */ } finally { setLoading(false); }
  }, [typeFilter]);

  useEffect(() => { load(); }, [load]);

  const findPath = async () => {
    if (!pathSource.trim() || !pathTarget.trim()) return;
    try {
      const r = await api.graphShortestPath(pathSource.trim(), pathTarget.trim());
      setPathResult(r as unknown as { path: string[] | null; length: number });
    } catch { setPathResult(null); }
  };

  if (loading) return <div className="flex items-center justify-center h-40" style={{ color: "var(--text-muted)" }}>Loading graph…</div>;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-2 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
        <TabBtn active={activeView === "nodes"} icon={Layers} label={`Nodes (${nodes.length})`} onClick={() => setActiveView("nodes")} />
        <TabBtn active={activeView === "edges"} icon={GitBranch} label={`Edges (${edges.length})`} onClick={() => setActiveView("edges")} />
        <TabBtn active={activeView === "components"} icon={Database} label={`Components (${components.length})`} onClick={() => setActiveView("components")} />
        <div className="flex-1" />
        <input value={typeFilter} onChange={e => setTypeFilter(e.target.value)} placeholder="Filter type…" className="memory-search text-xs" style={{ width: 120 }} />
        <button className="btn-ghost text-xs" onClick={load}><RefreshCw size={12} /></button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {activeView === "nodes" && (
          <>
            {nodes.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>No nodes in the graph yet.</p>}
            {nodes.map(n => (
              <div key={n.id} className="p-3 rounded-lg text-xs" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium" style={{ color: "var(--text-primary)" }}>{n.label}</span>
                  <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: "var(--bg)", color: "var(--accent)" }}>{n.node_type}</span>
                </div>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>ID: {n.id}</p>
                {Object.keys(n.properties).length > 0 && (
                  <pre className="mt-1 text-xs overflow-x-auto" style={{ color: "var(--text-secondary)" }}>
                    {JSON.stringify(n.properties, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </>
        )}

        {activeView === "edges" && (
          <>
            {edges.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>No edges in the graph yet.</p>}
            {edges.map(e => (
              <div key={e.id} className="flex items-center gap-2 p-2 rounded text-xs" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
                <span style={{ color: "var(--accent)" }}>{e.source_id.slice(0, 8)}</span>
                <span style={{ color: "var(--text-muted)" }}>—</span>
                <span className="px-1.5 py-0.5 rounded" style={{ background: "var(--bg)", color: "var(--green)" }}>{e.relation}</span>
                <span style={{ color: "var(--text-muted)" }}>→</span>
                <span style={{ color: "var(--accent)" }}>{e.target_id.slice(0, 8)}</span>
                <span className="ml-auto" style={{ color: "var(--text-muted)" }}>w={e.weight.toFixed(2)}</span>
              </div>
            ))}
          </>
        )}

        {activeView === "components" && (
          <>
            {/* Shortest path finder */}
            <div className="p-3 rounded-lg space-y-2" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
              <p className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>Shortest Path</p>
              <div className="flex gap-2">
                <input value={pathSource} onChange={e => setPathSource(e.target.value)} placeholder="Source node ID" className="memory-search text-xs flex-1" />
                <input value={pathTarget} onChange={e => setPathTarget(e.target.value)} placeholder="Target node ID" className="memory-search text-xs flex-1" />
                <button className="btn-primary text-xs" onClick={findPath}>Find</button>
              </div>
              {pathResult && (
                <div className="text-xs" style={{ color: pathResult.path ? "var(--green)" : "var(--red)" }}>
                  {pathResult.path ? `Path found (length ${pathResult.length}): ${pathResult.path.join(" → ")}` : "No path found"}
                </div>
              )}
            </div>

            {components.map((c, i) => (
              <div key={i} className="flex items-center justify-between p-2 rounded text-xs" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
                <span style={{ color: "var(--text-primary)" }}>Component {i + 1}</span>
                <span style={{ color: "var(--text-muted)" }}>{c.size} nodes</span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Hybrid Search Tab
// ---------------------------------------------------------------------------

function HybridSearchTab() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Array<{ content: string; source: string; score: number; metadata: Record<string, unknown> }>>([]);
  const [loading, setLoading] = useState(false);
  const [useVector, setUseVector] = useState(true);
  const [useGraph, setUseGraph] = useState(true);
  const [useKeyword, setUseKeyword] = useState(true);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await api.hybridSearch(query.trim(), 20, { use_vector: useVector, use_graph: useGraph, use_keyword: useKeyword });
      setResults(data.results ?? []);
    } catch { setResults([]); } finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex gap-2 mb-2">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSearch()}
            placeholder="Hybrid search across all memory backends…"
            className="memory-search text-xs flex-1"
          />
          <button className="btn-primary text-xs" onClick={handleSearch} disabled={loading}>
            {loading ? "Searching…" : "Search"}
          </button>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1 text-xs" style={{ color: "var(--text-secondary)" }}>
            <input type="checkbox" checked={useVector} onChange={e => setUseVector(e.target.checked)} />
            Vector
          </label>
          <label className="flex items-center gap-1 text-xs" style={{ color: "var(--text-secondary)" }}>
            <input type="checkbox" checked={useGraph} onChange={e => setUseGraph(e.target.checked)} />
            Graph
          </label>
          <label className="flex items-center gap-1 text-xs" style={{ color: "var(--text-secondary)" }}>
            <input type="checkbox" checked={useKeyword} onChange={e => setUseKeyword(e.target.checked)} />
            Keyword
          </label>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {results.length === 0 && !loading && (
          <div className="flex items-center justify-center h-40 text-xs" style={{ color: "var(--text-muted)" }}>
            {query ? "No results found" : "Enter a query to search all memory backends"}
          </div>
        )}
        {results.map((r, i) => (
          <div key={i} className="p-3 rounded-lg" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
            <div className="flex items-center justify-between mb-1">
              <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: "var(--bg)", color: "var(--green)" }}>{r.source}</span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>Score: {r.score.toFixed(3)}</span>
            </div>
            <p className="text-xs" style={{ color: "var(--text-primary)" }}>{r.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Export/Import Tab
// ---------------------------------------------------------------------------

function ExportImportTab() {
  const [exportData, setExportData] = useState<string | null>(null);
  const [exportFormat, setExportFormat] = useState<"json" | "markdown">("json");
  const [importData, setImportData] = useState("");
  const [importFormat, setImportFormat] = useState<"json" | "markdown">("json");
  const [msg, setMsg] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    setMsg(null);
    try {
      const data = await api.exportMemory(exportFormat);
      setExportData(data.data);
      setMsg(`Exported ${exportFormat} successfully`);
    } catch (e) { setMsg(`Export error: ${e}`); } finally { setExporting(false); }
  };

  const handleImport = async () => {
    if (!importData.trim()) return;
    setImporting(true);
    setMsg(null);
    try {
      const data = await api.importMemory(importData, importFormat);
      setMsg(`Imported: ${data.episodes_imported} episodes, ${data.entities_imported} entities, ${data.nodes_imported} nodes, ${data.edges_imported} edges`);
    } catch (e) { setMsg(`Import error: ${e}`); } finally { setImporting(false); }
  };

  const downloadExport = () => {
    if (!exportData) return;
    const blob = new Blob([exportData], { type: exportFormat === "json" ? "application/json" : "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aios-memory.${exportFormat === "json" ? "json" : "md"}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-4 space-y-6 overflow-y-auto h-full">
      {msg && (
        <div className="text-xs px-3 py-2 rounded" style={{ background: "var(--surface)", color: msg.includes("error") || msg.includes("Error") ? "var(--red)" : "var(--green)" }}>
          {msg}
        </div>
      )}

      {/* Export */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
          <Download size={14} /> Export Memory
        </h3>
        <div className="flex items-center gap-2">
          <select value={exportFormat} onChange={e => setExportFormat(e.target.value as "json" | "markdown")} className="memory-search text-xs" style={{ width: "auto" }}>
            <option value="json">JSON</option>
            <option value="markdown">Markdown</option>
          </select>
          <button className="btn-primary text-xs" onClick={handleExport} disabled={exporting}>
            {exporting ? "Exporting…" : "Export"}
          </button>
          {exportData && (
            <button className="btn-ghost text-xs" onClick={downloadExport}>
              Download
            </button>
          )}
        </div>
        {exportData && (
          <textarea
            readOnly
            value={exportData.slice(0, 5000)}
            className="memory-search text-xs w-full"
            style={{ height: 200, fontFamily: "monospace" }}
          />
        )}
      </div>

      {/* Import */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
          <Upload size={14} /> Import Memory
        </h3>
        <div className="flex items-center gap-2">
          <select value={importFormat} onChange={e => setImportFormat(e.target.value as "json" | "markdown")} className="memory-search text-xs" style={{ width: "auto" }}>
            <option value="json">JSON</option>
            <option value="markdown">Markdown</option>
          </select>
          <button className="btn-primary text-xs" onClick={handleImport} disabled={importing || !importData.trim()}>
            {importing ? "Importing…" : "Import"}
          </button>
        </div>
        <textarea
          value={importData}
          onChange={e => setImportData(e.target.value)}
          placeholder="Paste memory data to import…"
          className="memory-search text-xs w-full"
          style={{ height: 200, fontFamily: "monospace" }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Workspace
// ---------------------------------------------------------------------------

export function MemoryExplorerWorkspace() {
  const [tab, setTab] = useState<Tab>("overview");

  const tabs: { id: Tab; icon: React.ElementType; label: string }[] = [
    { id: "overview", icon: Activity, label: "Overview" },
    { id: "workspaces", icon: Database, label: "Workspaces" },
    { id: "graph", icon: GitBranch, label: "Knowledge Graph" },
    { id: "search", icon: Search, label: "Hybrid Search" },
    { id: "export", icon: Download, label: "Import/Export" },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-4 py-2 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
        {tabs.map(t => (
          <TabBtn key={t.id} active={tab === t.id} icon={t.icon} label={t.label} onClick={() => setTab(t.id)} />
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {tab === "overview" && <OverviewTab />}
        {tab === "workspaces" && <WorkspacesTab />}
        {tab === "graph" && <GraphTab />}
        {tab === "search" && <HybridSearchTab />}
        {tab === "export" && <ExportImportTab />}
      </div>
    </div>
  );
}
