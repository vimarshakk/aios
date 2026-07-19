"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, ArrowLeft, Search, Plus, Trash2, Database, AlertCircle } from "lucide-react";
import { api, type HealthResponse } from "@/lib/api";
import Link from "next/link";

interface MemoryEntry {
  key: string;
  value: string;
}

export default function MemoryPage() {
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadMemories = async () => {
    setLoading(true);
    setError("");
    try {
      // We can query the default memory agent or call chat with "what do you know" or direct API
      // Since memory agent is backed by MemoryTool which stores in a shared global dict,
      // let's send a search/list message to the gateway to list them
      const res = await api.chat({
        message: "retrieve all memories",
        agent: "memory",
        mode: "single",
      });
      
      // Parse memories from response if possible. The response from MemoryAgent list is:
      // "• key: value" or similar format.
      const text = res.response;
      const parsed: MemoryEntry[] = [];
      const lines = text.split("\n");
      for (const line of lines) {
        const match = line.match(/^•\s*([^:]+):\s*(.*)/);
        if (match) {
          parsed.push({ key: match[1].trim(), value: match[2].trim() });
        }
      }
      setMemories(parsed);
    } catch (err) {
      setError("Failed to fetch memories from agent. Make sure gateway is running.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMemories();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey.trim() || !newValue.trim()) return;

    setLoading(true);
    try {
      await api.chat({
        message: `remember that ${newKey.trim()} is ${newValue.trim()}`,
        agent: "memory",
        mode: "single",
      });
      setNewKey("");
      setNewValue("");
      loadMemories();
    } catch (err) {
      setError("Failed to store memory.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (key: string) => {
    setLoading(true);
    try {
      await api.chat({
        message: `forget ${key}`,
        agent: "memory",
        mode: "single",
      });
      loadMemories();
    } catch (err) {
      setError("Failed to delete memory.");
    } finally {
      setLoading(false);
    }
  };

  const filteredMemories = memories.filter(
    (m) =>
      m.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.value.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ minHeight: "100dvh", background: "var(--aios-bg)", padding: "32px 40px" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 32 }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--aios-text-2)", textDecoration: "none", fontSize: "0.875rem" }}>
            <ArrowLeft size={16} /> Back to Chat
          </Link>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
          <div style={{ width: 40, height: 40, borderRadius: "50%", background: "linear-gradient(135deg, #a78bfa, #ec4899)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Brain size={18} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.03em" }}>Memory Browser</h1>
            <p style={{ color: "var(--aios-text-2)", fontSize: "0.85rem" }}>Browse, store, and manage your personal AI operating system memories</p>
          </div>
        </div>

        {error && (
          <div style={{ display: "flex", gap: 8, alignItems: "center", padding: "12px 16px", borderRadius: "var(--r-md)", background: "rgba(239, 68, 68, 0.15)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "var(--aios-red)", marginBottom: 24, fontSize: "0.85rem" }}>
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 24, alignItems: "start" }}>
          {/* Main List */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ position: "relative" }}>
              <input
                type="text"
                placeholder="Search memories..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 16px 10px 40px",
                  background: "var(--aios-surface)",
                  border: "1px solid var(--aios-border)",
                  borderRadius: "var(--r-md)",
                  color: "var(--aios-text)",
                  fontSize: "0.875rem",
                  outline: "none",
                }}
              />
              <Search size={16} style={{ position: "absolute", left: 14, top: 12, color: "var(--aios-text-3)" }} />
            </div>

            {loading && memories.length === 0 ? (
              <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
                <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
              </div>
            ) : filteredMemories.length === 0 ? (
              <div className="glass-card" style={{ padding: 40, textAlign: "center", color: "var(--aios-text-3)" }}>
                <Database size={32} style={{ margin: "0 auto 12px" }} />
                No memories found. Add one on the right or type in chat.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {filteredMemories.map((m) => (
                  <motion.div
                    key={m.key}
                    layout
                    className="glass-card"
                    style={{ padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontWeight: 700, color: "var(--aios-accent-2)", fontSize: "0.9rem", marginBottom: 2 }}>
                        {m.key}
                      </div>
                      <div style={{ fontSize: "0.85rem", color: "var(--aios-text)", wordBreak: "break-word" }}>
                        {m.value}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDelete(m.key)}
                      className="btn-icon"
                      style={{ border: "none", color: "var(--aios-red)", background: "rgba(239, 68, 68, 0.05)" }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </motion.div>
                ))}
              </div>
            )}
          </div>

          {/* Add Form */}
          <div className="glass-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
              <Plus size={16} /> Add Memory
            </h3>
            <form onSubmit={handleAdd} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", color: "var(--aios-text-3)", marginBottom: 4, fontWeight: 600 }}>KEY</label>
                <input
                  type="text"
                  placeholder="e.g. coffee preference"
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    background: "var(--aios-bg)",
                    border: "1px solid var(--aios-border)",
                    borderRadius: "var(--r-sm)",
                    color: "var(--aios-text)",
                    fontSize: "0.85rem",
                    outline: "none",
                  }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", color: "var(--aios-text-3)", marginBottom: 4, fontWeight: 600 }}>VALUE</label>
                <textarea
                  placeholder="e.g. Black coffee, no sugar"
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  rows={3}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    background: "var(--aios-bg)",
                    border: "1px solid var(--aios-border)",
                    borderRadius: "var(--r-sm)",
                    color: "var(--aios-text)",
                    fontSize: "0.85rem",
                    outline: "none",
                    resize: "none",
                  }}
                />
              </div>
              <button type="submit" disabled={loading} className="btn-primary" style={{ width: "100%", justifyContent: "center", marginTop: 8 }}>
                Add Entry
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
