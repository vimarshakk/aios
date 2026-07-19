/**
 * CollaborationManager — Shared workspaces and real-time collaboration.
 *
 * Provides:
 * - Shared workspace management
 * - Real-time cursor presence
 * - Collaborative editing indicators
 * - User roles and permissions
 * - Activity feed
 */

import { EventEmitter } from "events";

export interface Collaborator {
  id: string;
  name: string;
  avatar?: string;
  color: string;
  status: "online" | "away" | "offline";
  cursor?: CursorPosition;
  lastSeen: number;
}

export interface CursorPosition {
  x: number;
  y: number;
  element?: string;
  section?: string;
}

export interface SharedWorkspace {
  id: string;
  name: string;
  ownerId: string;
  collaborators: Collaborator[];
  createdAt: number;
  updatedAt: number;
  isPublic: boolean;
  permissions: WorkspacePermission[];
}

export interface WorkspacePermission {
  userId: string;
  role: "owner" | "editor" | "viewer";
  grantedAt: number;
  grantedBy: string;
}

export interface ActivityEntry {
  id: string;
  userId: string;
  userName: string;
  action: "join" | "leave" | "edit" | "comment" | "share" | "delete";
  target?: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

export interface CollaborationState {
  workspaces: SharedWorkspace[];
  activeWorkspace: string | null;
  collaborators: Collaborator[];
  activityFeed: ActivityEntry[];
}

export class CollaborationManager extends EventEmitter {
  private workspaces: Map<string, SharedWorkspace> = new Map();
  private collaborators: Map<string, Collaborator> = new Map();
  private activityFeed: ActivityEntry[] = [];
  private activeWorkspaceId: string | null = null;
  private userId: string;
  private userName: string;

  constructor(options?: { userId?: string; userName?: string }) {
    super();
    this.userId = options?.userId || "local-user";
    this.userName = options?.userName || "You";
  }

  /**
   * Create a new shared workspace.
   */
  createWorkspace(name: string, isPublic = false): SharedWorkspace {
    const workspace: SharedWorkspace = {
      id: `ws-${Date.now()}`,
      name,
      ownerId: this.userId,
      collaborators: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
      isPublic,
      permissions: [
        {
          userId: this.userId,
          role: "owner",
          grantedAt: Date.now(),
          grantedBy: this.userId,
        },
      ],
    };

    this.workspaces.set(workspace.id, workspace);
    this.addActivity("join", workspace.name);
    this.emit("workspace-created", workspace);

    return workspace;
  }

  /**
   * Get a workspace by ID.
   */
  getWorkspace(id: string): SharedWorkspace | undefined {
    return this.workspaces.get(id);
  }

  /**
   * Get all workspaces.
   */
  getWorkspaces(): SharedWorkspace[] {
    return Array.from(this.workspaces.values());
  }

  /**
   * Delete a workspace.
   */
  deleteWorkspace(id: string): boolean {
    const workspace = this.workspaces.get(id);
    if (!workspace || workspace.ownerId !== this.userId) return false;

    this.workspaces.delete(id);
    if (this.activeWorkspaceId === id) {
      this.activeWorkspaceId = null;
    }
    this.emit("workspace-deleted", id);
    return true;
  }

  /**
   * Set the active workspace.
   */
  setActiveWorkspace(id: string | null): void {
    this.activeWorkspaceId = id;
    this.emit("active-workspace-changed", id);
  }

  /**
   * Get the active workspace.
   */
  getActiveWorkspace(): SharedWorkspace | undefined {
    if (!this.activeWorkspaceId) return undefined;
    return this.workspaces.get(this.activeWorkspaceId);
  }

  /**
   * Add a collaborator to a workspace.
   */
  addCollaborator(workspaceId: string, collaborator: Omit<Collaborator, "lastSeen">): boolean {
    const workspace = this.workspaces.get(workspaceId);
    if (!workspace) return false;

    const existing = workspace.collaborators.find((c) => c.id === collaborator.id);
    if (existing) return false;

    workspace.collaborators.push({
      ...collaborator,
      lastSeen: Date.now(),
    });

    workspace.updatedAt = Date.now();
    this.collaborators.set(collaborator.id, {
      ...collaborator,
      lastSeen: Date.now(),
    });

    this.addActivity("share", workspace.name, collaborator.name);
    this.emit("collaborator-added", { workspaceId, collaborator });

    return true;
  }

  /**
   * Remove a collaborator from a workspace.
   */
  removeCollaborator(workspaceId: string, userId: string): boolean {
    const workspace = this.workspaces.get(workspaceId);
    if (!workspace) return false;

    const index = workspace.collaborators.findIndex((c) => c.id === userId);
    if (index === -1) return false;

    const removed = workspace.collaborators.splice(index, 1)[0];
    workspace.updatedAt = Date.now();
    this.collaborators.delete(userId);

    this.addActivity("leave", workspace.name, removed.name);
    this.emit("collaborator-removed", { workspaceId, userId });

    return true;
  }

  /**
   * Update collaborator cursor position.
   */
  updateCursor(userId: string, position: CursorPosition): void {
    const collaborator = this.collaborators.get(userId);
    if (collaborator) {
      collaborator.cursor = position;
      collaborator.lastSeen = Date.now();
      this.emit("cursor-updated", { userId, position });
    }
  }

  /**
   * Get all collaborators in the active workspace.
   */
  getActiveCollaborators(): Collaborator[] {
    if (!this.activeWorkspaceId) return [];
    const workspace = this.workspaces.get(this.activeWorkspaceId);
    return workspace?.collaborators || [];
  }

  /**
   * Set a collaborator's status.
   */
  setCollaboratorStatus(userId: string, status: Collaborator["status"]): void {
    const collaborator = this.collaborators.get(userId);
    if (collaborator) {
      collaborator.status = status;
      collaborator.lastSeen = Date.now();
      this.emit("collaborator-status-changed", { userId, status });
    }
  }

  /**
   * Grant a permission to a user.
   */
  grantPermission(workspaceId: string, userId: string, role: WorkspacePermission["role"]): boolean {
    const workspace = this.workspaces.get(workspaceId);
    if (!workspace) return false;

    const existing = workspace.permissions.find((p) => p.userId === userId);
    if (existing) {
      existing.role = role;
    } else {
      workspace.permissions.push({
        userId,
        role,
        grantedAt: Date.now(),
        grantedBy: this.userId,
      });
    }

    workspace.updatedAt = Date.now();
    this.emit("permission-granted", { workspaceId, userId, role });

    return true;
  }

  /**
   * Check if a user has a specific role.
   */
  hasPermission(workspaceId: string, userId: string, role: WorkspacePermission["role"]): boolean {
    const workspace = this.workspaces.get(workspaceId);
    if (!workspace) return false;

    const permission = workspace.permissions.find((p) => p.userId === userId);
    if (!permission) return false;

    const roleHierarchy: Record<string, number> = { owner: 3, editor: 2, viewer: 1 };
    return (roleHierarchy[permission.role] || 0) >= (roleHierarchy[role] || 0);
  }

  /**
   * Add an activity entry.
   */
  private addActivity(action: ActivityEntry["action"], target?: string, userName?: string): void {
    const entry: ActivityEntry = {
      id: `act-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      userId: this.userId,
      userName: userName || this.userName,
      action,
      target,
      timestamp: Date.now(),
    };

    this.activityFeed.unshift(entry);

    // Keep only last 100 entries
    if (this.activityFeed.length > 100) {
      this.activityFeed = this.activityFeed.slice(0, 100);
    }

    this.emit("activity", entry);
  }

  /**
   * Get the activity feed.
   */
  getActivityFeed(limit = 20): ActivityEntry[] {
    return this.activityFeed.slice(0, limit);
  }

  /**
   * Get collaboration state.
   */
  getState(): CollaborationState {
    return {
      workspaces: this.getWorkspaces(),
      activeWorkspace: this.activeWorkspaceId,
      collaborators: Array.from(this.collaborators.values()),
      activityFeed: this.getActivityFeed(),
    };
  }

  /**
   * Destroy the collaboration manager.
   */
  destroy(): void {
    this.workspaces.clear();
    this.collaborators.clear();
    this.activityFeed = [];
    this.activeWorkspaceId = null;
  }
}

export default CollaborationManager;
