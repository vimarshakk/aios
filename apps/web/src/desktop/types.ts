"use client";

import type { ComponentType, ReactNode } from "react";

// ---------------------------------------------------------------------------
// Workspace
// ---------------------------------------------------------------------------

export type AppMode = "normal" | "developer";

export interface WorkspaceDefinition {
  id: string;
  uri: string; // aios://<id>
  title: string;
  icon: ComponentType<{ size?: number; className?: string }>;
  component: ComponentType;
  shortcut?: string;
  defaultRightPanel?: string;
  searchable?: boolean;
  group?: "core" | "tools" | "system" | "dev";
  modes?: AppMode[];
}

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------

export interface PanelState {
  width: number;
  collapsed: boolean;
}

export interface LayoutState {
  sidebar: PanelState;
  rightPanel: PanelState;
  rightPanelTab: string | null;
  compactMode: boolean;
}

// ---------------------------------------------------------------------------
// Theme
// ---------------------------------------------------------------------------

export type ThemeMode = "light" | "dark" | "system";
export type AccentColor = "orange" | "graphite" | "emerald" | "violet";

export interface ThemeState {
  mode: ThemeMode;
  accent: AccentColor;
}

// ---------------------------------------------------------------------------
// Session
// ---------------------------------------------------------------------------

export interface SessionState {
  currentProject: string | null;
  assistantName: string;
}

// ---------------------------------------------------------------------------
// Command Palette
// ---------------------------------------------------------------------------

export interface CommandItem {
  id: string;
  label: string;
  shortcut?: string;
  icon?: ComponentType<{ size?: number }>;
  group: string;
  action: () => void;
}

// ---------------------------------------------------------------------------
// Dev Mode — Workforce
// ---------------------------------------------------------------------------

export type WorkerStatus = "idle" | "running" | "busy" | "offline" | "error";
export type WorkerRole = "architect" | "backend" | "frontend" | "qa" | "devops" | "researcher" | "designer" | "reviewer";

export interface WorkerCapability {
  name: string;
  description: string;
  level: "primary" | "secondary";
}

export interface WorkerTerminal {
  workerId: string;
  stdout: string[];
  stderr: string[];
  lastActivity: number;
}

export interface Worker {
  id: string;
  name: string;
  type: "cli" | "ide" | "service" | "agent";
  command: string;
  status: WorkerStatus;
  role: WorkerRole;
  capabilities: WorkerCapability[];
  assignedTask?: string;
  currentGoalId?: string;
  startedAt?: number;
  lastActive: number;
  tokensUsed: number;
  cost: number;
  pid?: number;
  exitCode?: number;
}

export interface TaskNode {
  id: string;
  name: string;
  status: "pending" | "assigned" | "running" | "completed" | "failed" | "reviewing" | "approved";
  assignedWorker?: string;
  workerRole: WorkerRole;
  dependencies: string[];
  dependents: string[];
  input?: string;
  output?: string;
  error?: string;
  startedAt?: number;
  completedAt?: number;
  reviewNotes?: string;
}

export interface ReviewRequest {
  id: string;
  taskId: string;
  taskName: string;
  sourceWorker: string;
  reviewWorker: string;
  sourceOutput: string;
  status: "pending" | "running" | "approved" | "changes_requested" | "rejected";
  reviewNotes?: string;
  createdAt: number;
  completedAt?: number;
}

export interface BuildArtifact {
  id: string;
  name: string;
  path: string;
  type: "file" | "directory" | "test" | "config" | "deployment";
  status: "generated" | "modified" | "deleted" | "unchanged";
  workerId: string;
  goalId?: string;
  createdAt: number;
  size?: number;
}

export interface Repository {
  id: string;
  name: string;
  path: string;
  url?: string;
  branch: string;
  status: "active" | "idle" | "error" | "building";
  language: string;
  files: number;
  lastCommit?: string;
  lastCommitAt?: number;
  workers: string[];
  uncommittedChanges: number;
}

export interface DevModeState {
  workers: Worker[];
  taskGraph: TaskNode[];
  reviews: ReviewRequest[];
  artifacts: BuildArtifact[];
  activeGoalId?: string;
  goalTitle?: string;
  goalProgress: number;
}
