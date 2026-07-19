"use client";

import { create } from "zustand";
import type { PanelState } from "../types";

const STORAGE_KEY = "aios-layout";
const DOCK_DEFAULT = 64;
const INSPECTOR_DEFAULT = 360;

export type AppMode = "normal" | "developer";

interface LayoutStore {
  dock: PanelState;
  inspector: PanelState;
  inspectorTab: string | null;
  appMode: AppMode;
  compactMode: boolean;
  setDockWidth: (w: number) => void;
  toggleDock: () => void;
  setInspectorWidth: (w: number) => void;
  toggleInspector: () => void;
  setInspectorTab: (tab: string | null) => void;
  setAppMode: (mode: AppMode) => void;
  toggleAppMode: () => void;
  setCompactMode: (v: boolean) => void;
}

function loadLayout(): Partial<LayoutStore> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return {};
}

function persist(state: LayoutStore) {
  if (typeof window === "undefined") return;
  try {
    const { dock, inspector, inspectorTab, appMode, compactMode } = state;
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ dock, inspector, inspectorTab, appMode, compactMode }));
  } catch { /* ignore */ }
}

export const useLayoutStore = create<LayoutStore>((set, get) => {
  const saved = loadLayout();

  return {
    dock: saved.dock ?? { width: DOCK_DEFAULT, collapsed: false },
    inspector: saved.inspector ?? { width: INSPECTOR_DEFAULT, collapsed: false },
    inspectorTab: saved.inspectorTab ?? "ai-core",
    appMode: saved.appMode ?? "normal",
    compactMode: saved.compactMode ?? false,

    setDockWidth: (w) => {
      set({ dock: { ...get().dock, width: Math.min(Math.max(w, 48), 96) } });
      persist(get());
    },
    toggleDock: () => {
      const s = get().dock;
      set({ dock: { ...s, collapsed: !s.collapsed } });
      persist(get());
    },
    setInspectorWidth: (w) => {
      set({ inspector: { ...get().inspector, width: Math.min(Math.max(w, 280), 520) } });
      persist(get());
    },
    toggleInspector: () => {
      const r = get().inspector;
      set({ inspector: { ...r, collapsed: !r.collapsed } });
      persist(get());
    },
    setInspectorTab: (tab) => {
      set({ inspectorTab: tab, inspector: { ...get().inspector, collapsed: tab === null } });
      persist(get());
    },
    setAppMode: (mode) => {
      set({ appMode: mode });
      persist(get());
    },
    toggleAppMode: () => {
      const current = get().appMode;
      set({ appMode: current === "normal" ? "developer" : "normal" });
      persist(get());
    },
    setCompactMode: (v) => {
      set({ compactMode: v });
      persist(get());
    },
  };
});
