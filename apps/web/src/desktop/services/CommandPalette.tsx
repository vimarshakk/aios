"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  MessageSquare, FolderKanban, Target, Brain, Users,
  Wrench, ScrollText, Settings, Search, Moon, Sun, Palette,
  Terminal, Command,
} from "lucide-react";
import { useWorkspaceStore, useLayoutStore, useThemeStore } from "../state";
import { workspaces } from "../workspaces/registry";
import type { CommandItem } from "../types";

interface CommandPaletteProps {
  onClose: () => void;
}

export function CommandPalette({ onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Build command list
  const commands: CommandItem[] = [
    // Workspace navigation
    ...workspaces.map((ws) => ({
      id: `workspace:${ws.id}`,
      label: `Open ${ws.title}`,
      shortcut: ws.shortcut,
      icon: ws.icon,
      group: "Workspaces",
      action: () => { useWorkspaceStore.getState().setActive(ws.id); onClose(); },
    })),
    // Theme
    {
      id: "theme:dark",
      label: "Switch to Dark theme",
      icon: Moon,
      group: "Appearance",
      action: () => { useThemeStore.getState().setMode("dark"); onClose(); },
    },
    {
      id: "theme:light",
      label: "Switch to Light theme",
      icon: Sun,
      group: "Appearance",
      action: () => { useThemeStore.getState().setMode("light"); onClose(); },
    },
    {
      id: "theme:orange",
      label: "Accent: Orange",
      icon: Palette,
      group: "Appearance",
      action: () => { useThemeStore.getState().setAccent("orange"); onClose(); },
    },
    {
      id: "theme:emerald",
      label: "Accent: Emerald",
      icon: Palette,
      group: "Appearance",
      action: () => { useThemeStore.getState().setAccent("emerald"); onClose(); },
    },
    {
      id: "theme:violet",
      label: "Accent: Violet",
      icon: Palette,
      group: "Appearance",
      action: () => { useThemeStore.getState().setAccent("violet"); onClose(); },
    },
    {
      id: "theme:graphite",
      label: "Accent: Graphite",
      icon: Palette,
      group: "Appearance",
      action: () => { useThemeStore.getState().setAccent("graphite"); onClose(); },
    },
    // Layout
    {
      id: "layout:dock",
      label: "Toggle dock",
      shortcut: "⌘\\",
      icon: Command,
      group: "Layout",
      action: () => { useLayoutStore.getState().toggleDock(); onClose(); },
    },
    {
      id: "layout:inspector",
      label: "Toggle inspector",
      shortcut: "⌘]",
      icon: Command,
      group: "Layout",
      action: () => { useLayoutStore.getState().toggleInspector(); onClose(); },
    },
    {
      id: "mode:toggle",
      label: "Switch application mode",
      shortcut: "⌘⇧D",
      icon: Command,
      group: "Layout",
      action: () => { useLayoutStore.getState().toggleAppMode(); onClose(); },
    },
  ];

  // Filter
  const filtered = query
    ? commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()))
    : commands;

  // Group
  const grouped = filtered.reduce<Record<string, CommandItem[]>>((acc, cmd) => {
    (acc[cmd.group] ??= []).push(cmd);
    return acc;
  }, {});

  // Reset selection on query change
  useEffect(() => { setSelectedIdx(0); }, [query]);

  // Focus input
  useEffect(() => { inputRef.current?.focus(); }, []);

  // Scroll selected into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${selectedIdx}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [selectedIdx]);

  const execute = useCallback((cmd: CommandItem) => {
    cmd.action();
  }, []);

  // Keyboard navigation
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(i + 1, filtered.length - 1));
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(i - 1, 0));
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      if (filtered[selectedIdx]) execute(filtered[selectedIdx]);
      return;
    }
  };

  let flatIdx = 0;

  return (
    <div className="command-palette-overlay" onClick={onClose}>
      <div
        className="command-palette"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
          <Search size={16} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search commands, workspaces, settings…"
            className="flex-1 bg-transparent outline-none text-sm"
            style={{ color: "var(--text-primary)" }}
          />
          <kbd
            className="text-[0.6rem] px-1.5 py-0.5 rounded"
            style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-muted)" }}
          >
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-[320px] overflow-y-auto py-1">
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group}>
              <div
                className="px-4 py-1.5 text-[0.6rem] font-semibold uppercase tracking-wider"
                style={{ color: "var(--text-muted)" }}
              >
                {group}
              </div>
              {items.map((cmd) => {
                const idx = flatIdx++;
                const Icon = cmd.icon;
                const isSelected = idx === selectedIdx;
                return (
                  <button
                    key={cmd.id}
                    data-idx={idx}
                    className="flex items-center gap-3 w-full px-4 py-2 text-left text-sm transition-colors"
                    style={{
                      background: isSelected ? "var(--surface-hover)" : "transparent",
                      color: "var(--text-primary)",
                      border: "none",
                      cursor: "pointer",
                    }}
                    onMouseEnter={() => setSelectedIdx(idx)}
                    onClick={() => execute(cmd)}
                  >
                    {Icon && (
                          <span style={{ color: "var(--text-muted)", flexShrink: 0, display: "inline-flex" }}>
                            <Icon size={15} />
                          </span>
                        )}
                    <span className="flex-1 truncate">{cmd.label}</span>
                    {cmd.shortcut && (
                      <kbd
                        className="text-[0.6rem] px-1.5 py-0.5 rounded"
                        style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-muted)" }}
                      >
                        {cmd.shortcut}
                      </kbd>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="px-4 py-8 text-center text-sm" style={{ color: "var(--text-muted)" }}>
              No results found.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
