"use client";

import { useLayoutStore, useWorkspaceStore, useSessionStore } from "../state";
import { workspaces } from "../workspaces/registry";
import { cn } from "@/lib/cn";
import {
  Bot, Plus, Search, ChevronDown,
} from "lucide-react";
import { useState } from "react";

export function Sidebar() {
  const { sidebar, toggleSidebar } = useLayoutStore();
  const { activeId, setActive } = useWorkspaceStore();
  const { currentProject } = useSessionStore();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);

  const filtered = searchQuery
    ? workspaces.filter((w) =>
        w.title.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : workspaces;

  const core = filtered.filter((w) => w.group === "core");
  const tools = filtered.filter((w) => w.group === "tools");
  const system = filtered.filter((w) => w.group === "system");

  return (
    <div className="sidebar" style={{ width: sidebar.width }}>
      {/* Logo */}
      <div className="sidebar-logo">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold"
          style={{ background: "var(--accent-glow)", color: "var(--accent)" }}
        >
          <Bot size={18} />
        </div>
        <div className="flex flex-col min-w-0">
          <span className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
            AIOS
          </span>
          <span className="text-[0.6rem] truncate" style={{ color: "var(--text-muted)" }}>
            {currentProject || "No project"}
          </span>
        </div>
        <div className="ml-auto flex items-center gap-1">
          <button
            className="btn-icon"
            style={{ width: 26, height: 26, border: "none" }}
            onClick={() => setSearchOpen(!searchOpen)}
            title="Search workspaces"
          >
            <Search size={14} />
          </button>
        </div>
      </div>

      {/* Search */}
      {searchOpen && (
        <div className="px-3 py-2" style={{ borderBottom: "1px solid var(--border)" }}>
          <input
            autoFocus
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search…"
            className="w-full px-3 py-1.5 rounded-md text-sm outline-none"
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
            }}
            onKeyDown={(e) => {
              if (e.key === "Escape") {
                setSearchOpen(false);
                setSearchQuery("");
              }
            }}
          />
        </div>
      )}

      {/* New Goal button */}
      <div className="px-3 pt-3 pb-1">
        <button
          className="btn-primary w-full justify-center text-xs"
          style={{ padding: "7px 0" }}
        >
          <Plus size={14} />
          New Goal
        </button>
      </div>

      {/* Workspace navigation */}
      <nav className="flex-1 overflow-y-auto pt-1 pb-4">
        {core.length > 0 && (
          <>
            <div className="sidebar-section">Workspace</div>
            {core.map((ws) => (
              <WorkspaceItem
                key={ws.id}
                ws={ws}
                active={activeId === ws.id}
                onSelect={() => setActive(ws.id)}
              />
            ))}
          </>
        )}

        {tools.length > 0 && (
          <>
            <div className="sidebar-section">Tools</div>
            {tools.map((ws) => (
              <WorkspaceItem
                key={ws.id}
                ws={ws}
                active={activeId === ws.id}
                onSelect={() => setActive(ws.id)}
              />
            ))}
          </>
        )}

        {system.length > 0 && (
          <>
            <div className="sidebar-section">System</div>
            {system.map((ws) => (
              <WorkspaceItem
                key={ws.id}
                ws={ws}
                active={activeId === ws.id}
                onSelect={() => setActive(ws.id)}
              />
            ))}
          </>
        )}
      </nav>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Workspace item
// ---------------------------------------------------------------------------

function WorkspaceItem({
  ws,
  active,
  onSelect,
}: {
  ws: (typeof workspaces)[number];
  active: boolean;
  onSelect: () => void;
}) {
  const Icon = ws.icon;
  return (
    <button
      className={cn("sidebar-item w-full text-left", active && "active")}
      onClick={onSelect}
    >
      <Icon size={16} />
      <span className="truncate">{ws.title}</span>
      {ws.shortcut && <span className="shortcut">{ws.shortcut}</span>}
    </button>
  );
}
