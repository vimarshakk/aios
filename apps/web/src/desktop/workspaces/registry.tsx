"use client";

import type { ComponentType } from "react";
import {
  MessageSquare, FolderKanban, Target, Brain, Users,
  Wrench, ScrollText, Settings, Layers, Zap,
  LayoutDashboard,
  type LucideIcon,
} from "lucide-react";
import type { WorkspaceDefinition, AppMode } from "../types";

// ---------------------------------------------------------------------------
// Mode-aware workspace registry
// ---------------------------------------------------------------------------

export interface WorkspaceDefinitionWithMode extends WorkspaceDefinition {
  modes: AppMode[];
}

export const allWorkspaces: WorkspaceDefinitionWithMode[] = [
  // --- Shared (all modes) ---
  {
    id: "mission-control",
    uri: "aios://mission-control",
    title: "Mission Control",
    icon: LayoutDashboard,
    component: null as any, // lazy loaded below
    shortcut: "⌘0",
    group: "core",
    modes: ["normal", "developer"],
    searchable: true,
  },
  {
    id: "settings",
    uri: "aios://settings",
    title: "Settings",
    icon: Settings,
    component: null as any,
    shortcut: "⌘,",
    group: "system",
    modes: ["normal", "developer"],
    searchable: true,
  },

  // --- Normal mode ---
  {
    id: "conversation",
    uri: "aios://conversation",
    title: "Conversation",
    icon: MessageSquare,
    component: null as any,
    shortcut: "⌘1",
    group: "core",
    modes: ["normal"],
    searchable: true,
  },
  {
    id: "goals",
    uri: "aios://goals",
    title: "Goals",
    icon: Target,
    component: null as any,
    shortcut: "⌘G",
    group: "core",
    modes: ["normal"],
    searchable: true,
  },
  {
    id: "projects",
    uri: "aios://projects",
    title: "Projects",
    icon: FolderKanban,
    component: null as any,
    shortcut: "⌘2",
    group: "core",
    modes: ["normal"],
    searchable: true,
  },
  {
    id: "memory",
    uri: "aios://memory",
    title: "Memory",
    icon: Brain,
    component: null as any,
    shortcut: "⌘M",
    group: "tools",
    modes: ["normal"],
    searchable: true,
  },
  {
    id: "memory-explorer",
    uri: "aios://memory-explorer",
    title: "Memory Explorer",
    icon: Layers,
    component: null as any,
    shortcut: "⌘E",
    group: "tools",
    modes: ["normal"],
    searchable: true,
  },
  {
    id: "agents",
    uri: "aios://agents",
    title: "Agents",
    icon: Users,
    component: null as any,
    shortcut: "⌘A",
    group: "tools",
    modes: ["normal"],
    searchable: true,
  },
  {
    id: "skills",
    uri: "aios://skills",
    title: "Skills",
    icon: Wrench,
    component: null as any,
    shortcut: "⌘S",
    group: "tools",
    modes: ["normal"],
    searchable: true,
  },
  {
    id: "logs",
    uri: "aios://logs",
    title: "Logs",
    icon: ScrollText,
    component: null as any,
    shortcut: "⌘L",
    group: "system",
    modes: ["normal"],
    searchable: true,
  },

  // --- Developer mode ---
  {
    id: "dev-workforce",
    uri: "aios://dev-workforce",
    title: "Workforce",
    icon: Users,
    component: null as any,
    group: "dev",
    modes: ["developer"],
    searchable: true,
  },
  {
    id: "dev-repositories",
    uri: "aios://dev-repositories",
    title: "Repositories",
    icon: FolderKanban,
    component: null as any,
    group: "dev",
    modes: ["developer"],
    searchable: true,
  },
  {
    id: "dev-consoles",
    uri: "aios://dev-consoles",
    title: "Consoles",
    icon: ScrollText,
    component: null as any,
    group: "dev",
    modes: ["developer"],
    searchable: true,
  },
  {
    id: "dev-reviews",
    uri: "aios://dev-reviews",
    title: "Reviews",
    icon: Wrench,
    component: null as any,
    group: "dev",
    modes: ["developer"],
    searchable: true,
  },
];

// ---------------------------------------------------------------------------
// Lazy component loading — avoids circular imports
// ---------------------------------------------------------------------------

// We use a loader pattern so the registry doesn't need to import every workspace component at build time.
const COMPONENT_LOADERS: Record<string, () => Promise<{ default: ComponentType }>> = {
  "mission-control": () => import("./MissionControl").then(m => m),
  "conversation": () => import("./Conversation").then(m => m),
  "goals": () => import("./Goals").then(m => m),
  "projects": () => import("./Projects").then(m => m),
  "memory": () => import("./Memory").then(m => m),
  "memory-explorer": () => import("./MemoryExplorer").then(m => m),
  "agents": () => import("./Agents").then(m => m),
  "skills": () => import("./Skills").then(m => m),
  "logs": () => import("./Logs").then(m => m),
  "settings": () => import("./Settings").then(m => m),
  "dev-workforce": () => import("./WorkforceWorkspace").then(m => m),
  "dev-repositories": () => import("./RepositoriesWorkspace").then(m => m),
  "dev-consoles": () => import("./ConsolesWorkspace").then(m => m),
  "dev-reviews": () => import("./ReviewsWorkspace").then(m => m),
};

// Resolve components eagerly for simplicity (Next.js bundler handles code-splitting)
let resolvedComponents: Record<string, ComponentType> = {};

function resolveComponents() {
  if (Object.keys(resolvedComponents).length > 0) return;

  // Import all workspace components synchronously for initial render
  const components: Record<string, any> = {};

  // These are all statically imported in the old registry, so they're already in the bundle
  try { components["mission-control"] = require("./MissionControl").MissionControl; } catch {}
  try { components["conversation"] = require("./Conversation").ConversationWorkspace; } catch {}
  try { components["goals"] = require("./Goals").GoalsWorkspace; } catch {}
  try { components["projects"] = require("./Projects").ProjectsWorkspace; } catch {}
  try { components["memory"] = require("./Memory").MemoryWorkspace; } catch {}
  try { components["memory-explorer"] = require("./MemoryExplorer").MemoryExplorerWorkspace; } catch {}
  try { components["agents"] = require("./Agents").AgentsWorkspace; } catch {}
  try { components["skills"] = require("./Skills").SkillsWorkspace; } catch {}
  try { components["logs"] = require("./Logs").LogsWorkspace; } catch {}
  try { components["settings"] = require("./Settings").SettingsWorkspace; } catch {}
  try { components["dev-workforce"] = require("./WorkforceWorkspace").WorkforceWorkspace; } catch {}
  try { components["dev-repositories"] = require("./RepositoriesWorkspace").RepositoriesWorkspace; } catch {}
  try { components["dev-consoles"] = require("./ConsolesWorkspace").ConsolesWorkspace; } catch {}
  try { components["dev-reviews"] = require("./ReviewsWorkspace").ReviewsWorkspace; } catch {}

  resolvedComponents = components;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function getWorkspacesForMode(mode: AppMode): WorkspaceDefinition[] {
  resolveComponents();
  return allWorkspaces
    .filter((w) => w.modes.includes(mode))
    .map((w) => ({
      ...w,
      component: resolvedComponents[w.id] || w.component,
    }));
}

export function getWorkspace(id: string): WorkspaceDefinition | undefined {
  resolveComponents();
  const def = allWorkspaces.find((w) => w.id === id);
  if (!def) return undefined;
  return {
    ...def,
    component: resolvedComponents[def.id] || def.component,
  };
}

export function getWorkspaceByUri(uri: string): WorkspaceDefinition | undefined {
  const def = allWorkspaces.find((w) => w.uri === uri);
  return def ? getWorkspace(def.id) : undefined;
}

export function searchWorkspaces(query: string, mode?: AppMode): WorkspaceDefinition[] {
  const q = query.toLowerCase();
  const pool = mode ? allWorkspaces.filter((w) => w.modes.includes(mode)) : allWorkspaces;
  return pool
    .filter((w) => w.title.toLowerCase().includes(q) || w.uri.toLowerCase().includes(q))
    .map((w) => ({
      ...w,
      component: resolvedComponents[w.id] || w.component,
    }));
}

// Backward compat: flat `workspaces` array for code that still uses it
export const workspaces: WorkspaceDefinition[] = getWorkspacesForMode("normal");
