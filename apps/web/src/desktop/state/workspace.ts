"use client";

import { create } from "zustand";

const STORAGE_KEY = "aios-workspace";
const DEV_MODE_KEY = "aios-dev-mode";

interface WorkspaceStore {
  activeId: string;
  devMode: boolean;
  devModeTab: string;
  setActive: (id: string) => void;
  toggleDevMode: () => void;
  setDevModeTab: (tab: string) => void;
}

function loadWorkspace(): string {
  if (typeof window === "undefined") return "mission-control";
  return localStorage.getItem(STORAGE_KEY) || "mission-control";
}

function loadDevMode(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(DEV_MODE_KEY) === "true";
}

export const useWorkspaceStore = create<WorkspaceStore>((set) => ({
  activeId: loadWorkspace(),
  devMode: loadDevMode(),
  devModeTab: "workforce",
  setActive: (id) => {
    set({ activeId: id });
    localStorage.setItem(STORAGE_KEY, id);
  },
  toggleDevMode: () => {
    set((s) => {
      const next = !s.devMode;
      localStorage.setItem(DEV_MODE_KEY, String(next));
      if (next) {
        return { devMode: next, activeId: "dev-workforce" };
      }
      return { devMode: next, activeId: "mission-control" };
    });
  },
  setDevModeTab: (tab) => set({ devModeTab: tab }),
}));
