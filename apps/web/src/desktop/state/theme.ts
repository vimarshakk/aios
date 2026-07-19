"use client";

import { create } from "zustand";
import type { ThemeMode, AccentColor } from "../types";

const STORAGE_KEY = "aios-theme";

interface ThemeStore {
  mode: ThemeMode;
  accent: AccentColor;
  setMode: (mode: ThemeMode) => void;
  setAccent: (accent: AccentColor) => void;
  /** Resolve "system" to actual preference */
  resolved: "light" | "dark";
}

function getSystemPreference(): "light" | "dark" {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function loadTheme(): { mode: ThemeMode; accent: AccentColor } {
  if (typeof window === "undefined") return { mode: "dark", accent: "orange" };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return { mode: "dark", accent: "orange" };
}

export const useThemeStore = create<ThemeStore>((set, get) => {
  const saved = loadTheme();
  const resolved = saved.mode === "system" ? getSystemPreference() : saved.mode;

  return {
    ...saved,
    resolved,
    setMode: (mode) => {
      const resolved = mode === "system" ? getSystemPreference() : mode;
      set({ mode, resolved });
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...get(), mode }));
    },
    setAccent: (accent) => {
      set({ accent });
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...get(), accent }));
    },
  };
});
