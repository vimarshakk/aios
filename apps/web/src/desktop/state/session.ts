"use client";

import { create } from "zustand";

interface SessionStore {
  currentProject: string | null;
  assistantName: string;
  setProject: (name: string | null) => void;
  setAssistantName: (name: string) => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  currentProject: "AIOS",
  assistantName: typeof process !== "undefined"
    ? process.env.NEXT_PUBLIC_ASSISTANT_NAME || "AIOS"
    : "AIOS",
  setProject: (name) => set({ currentProject: name }),
  setAssistantName: (name) => set({ assistantName: name }),
}));
