"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  Brain, Search, Plus, Tag, Clock,
} from "lucide-react";
import { api, type MemoryEntry } from "@/lib/api";

const TYPE_CONFIG: Record<string, { color: string; label: string }> = {
  fact: { color: "var(--accent)", label: "Fact" },
  preference: { color: "var(--green)", label: "Preference" },
  conversation: { color: "var(--yellow)", label: "Conversation" },
  entity: { color: "var(--red)", label: "Entity" },
};

export function MemoryWorkspace() {
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rememberOpen, setRememberOpen] = useState(false);
  const [rememberContent, setRememberContent] = useState("");
  const [rememberTags, setRememberTags] = useState("");
  const [rememberType, setRememberType] = useState("fact");
  const [saving, setSaving] = useState(false);
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load recent memories on mount
  const fetchRecent = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.recentMemory(30);
      setMemories(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRecent();
  }, [fetchRecent]);

  // Search memories with debounce
  const handleSearch = useCallback(async (query: string) => {
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    if (!query.trim()) {
      fetchRecent();
      return;
    }
    searchTimeout.current = setTimeout(async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await api.searchMemory(query);
        setMemories(data);
      } catch (e) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    }, 300);
  }, [fetchRecent]);

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    handleSearch(value);
  };

  // Remember a new memory
  const handleRemember = async () => {
    if (!rememberContent.trim()) return;
    try {
      setSaving(true);
      const tags = rememberTags.split(",").map((t) => t.trim()).filter(Boolean);
      await api.rememberMemory({
        content: rememberContent.trim(),
        tags,
        type: rememberType,
      });
      setRememberContent("");
      setRememberTags("");
      setRememberOpen(false);
      // Refresh
      if (searchQuery.trim()) {
        handleSearch(searchQuery);
      } else {
        await fetchRecent();
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const filtered = memories.filter((m) => {
    if (filterType && m.type !== filterType) return false;
    return true;
  });

  return (
    <div className="flex flex-col h-full">
      {/* Search + filters */}
      <div className="px-6 py-3 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
            <input
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Search memories…"
              className="memory-search"
            />
          </div>
          <button className="btn-primary text-xs" onClick={() => setRememberOpen(!rememberOpen)}>
            <Plus size={14} />
            Remember
          </button>
        </div>
        <div className="flex items-center gap-2 mt-2">
          {Object.entries(TYPE_CONFIG).map(([type, cfg]) => (
            <button
              key={type}
              className={`memory-type-btn ${filterType === type ? "active" : ""}`}
              onClick={() => setFilterType(filterType === type ? null : type)}
              style={filterType === type ? { borderColor: cfg.color, color: cfg.color } : {}}
            >
              {cfg.label}
            </button>
          ))}
        </div>
      </div>

      {/* Remember form */}
      {rememberOpen && (
        <div className="px-6 py-3 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex flex-col gap-2">
            <textarea
              value={rememberContent}
              onChange={(e) => setRememberContent(e.target.value)}
              placeholder="What should I remember?"
              className="memory-search"
              rows={2}
              style={{ resize: "vertical" }}
            />
            <div className="flex gap-2">
              <input
                value={rememberTags}
                onChange={(e) => setRememberTags(e.target.value)}
                placeholder="Tags (comma-separated)"
                className="memory-search flex-1"
              />
              <select
                value={rememberType}
                onChange={(e) => setRememberType(e.target.value)}
                className="memory-search"
                style={{ width: "auto" }}
              >
                <option value="fact">Fact</option>
                <option value="preference">Preference</option>
                <option value="conversation">Conversation</option>
                <option value="entity">Entity</option>
              </select>
            </div>
            <div className="flex gap-2">
              <button
                className="btn-primary text-xs"
                onClick={handleRemember}
                disabled={saving || !rememberContent.trim()}
              >
                {saving ? "Saving…" : "Save Memory"}
              </button>
              <button
                className="text-xs"
                style={{ color: "var(--text-muted)" }}
                onClick={() => { setRememberOpen(false); setRememberContent(""); setRememberTags(""); }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Memory list */}
      <div className="flex-1 overflow-y-auto p-6 space-y-3">
        {loading && (
          <div className="flex items-center justify-center h-40" style={{ color: "var(--text-muted)" }}>
            Loading memories…
          </div>
        )}

        {!loading && error && (
          <div className="flex flex-col items-center justify-center h-40 gap-2 text-center">
            <p className="text-sm" style={{ color: "var(--red)" }}>Failed to load memories</p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>{error}</p>
            <button className="btn-primary text-xs mt-2" onClick={fetchRecent}>Retry</button>
          </div>
        )}

        {!loading && !error && filtered.map((memory) => {
          const isExpanded = expandedId === memory.id;
          const typeCfg = TYPE_CONFIG[memory.type] ?? { color: "var(--text-muted)", label: memory.type };

          return (
            <div key={memory.id} className="memory-card">
              <button
                className="memory-card-header"
                onClick={() => setExpandedId(isExpanded ? null : memory.id)}
              >
                <span
                  className="memory-type-dot"
                  style={{ background: typeCfg.color }}
                />
                <p className="memory-card-content">
                  {memory.content}
                </p>
                <span className="memory-confidence">
                  {Math.round(memory.confidence * 100)}%
                </span>
              </button>

              {isExpanded && (
                <div className="memory-card-body">
                  {memory.tags.length > 0 && (
                    <div className="memory-tags">
                      {memory.tags.map((tag) => (
                        <span key={tag} className="memory-tag">
                          <Tag size={10} />
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="memory-meta">
                    <span className="flex items-center gap-1">
                      <Clock size={12} />
                      {memory.created_at}
                    </span>
                    <span>Type: {typeCfg.label}</span>
                    {memory.source && <span>Source: {memory.source}</span>}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {!loading && !error && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 gap-3 text-center">
            <span style={{ color: "var(--text-muted)" }}><Brain size={28} /></span>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              {searchQuery ? "No memories match your search" : "No memories yet. Use Remember to store your first memory."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
