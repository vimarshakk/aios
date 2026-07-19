"use client";

import { useWorkspaceStore } from "../state/workspace";
import { useLayoutStore, type AppMode } from "../state/layout";
import { useThemeStore } from "../state/theme";
import { getWorkspacesForMode, getWorkspace } from "../workspaces/registry";
import { Dock } from "./Dock";
import { Inspector } from "./Inspector";
import { StatusBar } from "./StatusBar";
import { ResizablePanel } from "./ResizablePanel";
import { CommandPalette } from "../services/CommandPalette";
import { CommandBar } from "../components/CommandBar";
import { VoiceOverlay } from "../components/VoiceOverlay";
import { useEffect, useState, useCallback } from "react";
import { WorkspaceHeader } from "./WorkspaceHeader";

export function AppShell() {
  const { activeId, setActive } = useWorkspaceStore();
  const { dock, inspector, setDockWidth, setInspectorWidth, appMode, toggleAppMode } = useLayoutStore();
  const { mode, accent } = useThemeStore();
  const [cmdOpen, setCmdOpen] = useState(false);

  // Apply theme classes to <body>
  useEffect(() => {
    const b = document.body;
    b.className = b.className
      .replace(/theme-\w+/g, "")
      .replace(/accent-\w+/g, "")
      .trim();
    b.classList.add(`theme-${mode}`);
    b.classList.add(`accent-${accent}`);
  }, [mode, accent]);

  // When app mode changes, ensure the active workspace is valid for that mode
  useEffect(() => {
    const valid = getWorkspacesForMode(appMode);
    const currentValid = valid.some((w) => w.id === activeId);
    if (!currentValid) {
      // Default to mission control on mode switch
      setActive("mission-control");
    }
  }, [appMode, activeId, setActive]);

  // Global keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;

      // ⌘K — Command palette
      if (mod && e.key === "k") {
        e.preventDefault();
        setCmdOpen((o) => !o);
        return;
      }

      // ⌘0 — Mission Control
      if (mod && e.key === "0") {
        e.preventDefault();
        setActive("mission-control");
        return;
      }

      // ⌘1-8 — Switch workspace (mode-aware)
      if (mod && e.key >= "1" && e.key <= "8") {
        e.preventDefault();
        const idx = parseInt(e.key) - 1;
        const valid = getWorkspacesForMode(appMode);
        if (valid[idx]) setActive(valid[idx].id);
        return;
      }

      // ⌘, — Settings
      if (mod && e.key === ",") {
        e.preventDefault();
        setActive("settings");
        return;
      }

      // ⌘\ — Toggle dock
      if (mod && e.key === "\\") {
        e.preventDefault();
        useLayoutStore.getState().toggleDock();
        return;
      }

      // ⌘] — Toggle inspector
      if (mod && e.key === "]") {
        e.preventDefault();
        useLayoutStore.getState().toggleInspector();
        return;
      }

      // ⌘⇧D — Toggle application mode (Normal ↔ Developer)
      const toggleDevMode = toggleAppMode; // alias for backward compat
      if (mod && e.shiftKey && e.key.toLowerCase() === "d") {
        e.preventDefault();
        toggleDevMode();
        return;
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [appMode, setActive, toggleAppMode]);

  const ActiveComponent = getWorkspace(activeId)?.component;
  const isConversation = activeId === "conversation";

  // For non-conversation workspaces: command bar sends to conversation
  const handleGlobalExecute = useCallback((message: string, _opts: { agent: string; model: string }) => {
    sessionStorage.setItem("aios-pending-message", message);
    setActive("conversation");
  }, [setActive]);

  const handleGlobalGoal = useCallback((message: string) => {
    sessionStorage.setItem("aios-pending-goal", message);
    setActive("conversation");
  }, [setActive]);

  return (
    <div
      style={{
        height: "100vh",
        width: "100vw",
        display: "flex",
        flexDirection: "column",
        background: "var(--bg)",
        overflow: "hidden",
      }}
    >
      {/* Main 3-panel area */}
      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        {/* Dock (icon-only left rail) */}
        <ResizablePanel
          width={dock.width}
          minWidth={48}
          maxWidth={96}
          side="left"
          collapsed={dock.collapsed}
          onResize={setDockWidth}
        >
          <Dock />
        </ResizablePanel>

        {/* Center: workspace header + active workspace */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          <WorkspaceHeader />
          <main
            style={{
              flex: 1,
              overflow: "auto",
              background: "var(--bg)",
            }}
          >
            {ActiveComponent && <ActiveComponent />}
          </main>
        </div>

        {/* Inspector (generic right panel) */}
        {!inspector.collapsed && (
          <ResizablePanel
            width={inspector.width}
            minWidth={280}
            maxWidth={520}
            side="right"
            collapsed={inspector.collapsed}
            onResize={setInspectorWidth}
          >
            <Inspector />
          </ResizablePanel>
        )}
      </div>

      {/* Command bar — visible on non-mission-control workspaces */}
      {activeId !== "mission-control" && (
        <CommandBar onExecute={handleGlobalExecute} onGoal={handleGlobalGoal} />
      )}

      {/* Status bar (bottom) */}
      <StatusBar />

      {/* Voice overlay */}
      <VoiceOverlay />

      {/* Command palette */}
      {cmdOpen && <CommandPalette onClose={() => setCmdOpen(false)} />}
    </div>
  );
}
