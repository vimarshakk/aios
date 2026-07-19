/**
 * Preload script — Exposes safe APIs to renderer via contextBridge.
 *
 * This runs in a sandboxed context with access to ipcRenderer.
 * It exposes a typed `aios` object on window for the renderer to use.
 */

import { contextBridge, ipcRenderer } from "electron";

// Define the API shape exposed to renderer
export interface AiosDesktopAPI {
  // Window management
  window: {
    minimize: () => Promise<void>;
    maximize: () => Promise<void>;
    close: () => Promise<void>;
    focus: () => Promise<void>;
    isVisible: () => Promise<boolean>;
  };

  // App info
  app: {
    version: () => Promise<string>;
    name: () => Promise<string>;
    platform: () => Promise<string>;
    isPackaged: () => Promise<boolean>;
  };

  // System
  system: {
    screenSize: () => Promise<{ width: number; height: number }>;
    openExternal: (url: string) => Promise<void>;
    showItemInFolder: (fullPath: string) => Promise<void>;
  };

  // Dialogs
  dialog: {
    openFile: (options?: Electron.OpenDialogOptions) => Promise<string[] | null>;
    saveFile: (options?: Electron.SaveDialogOptions) => Promise<string | null>;
  };

  // Persistent store
  store: {
    get: <T = unknown>(key: string) => Promise<T>;
    set: (key: string, value: unknown) => Promise<void>;
    delete: (key: string) => Promise<void>;
    clear: () => Promise<void>;
  };

  // Notifications
  notification: {
    send: (options: { title: string; body: string }) => Promise<void>;
  };

  // Auto-update
  update: {
    check: () => Promise<void>;
    install: () => Promise<void>;
    status: () => Promise<{
      checking: boolean;
      available: boolean;
      downloaded: boolean;
      info: { version: string; releaseDate: string } | null;
      error: string | null;
    }>;
    on: (channel: string, callback: (...args: unknown[]) => void) => () => void;
  };

  // Navigation
  navigate: (workspaceId: string) => Promise<void>;

  // Deep links
  deepLink: {
    register: () => Promise<boolean>;
    on: (callback: (data: { path: string; params: URLSearchParams }) => void) => () => void;
  };

  // Events from main process
  on: (channel: string, callback: (...args: unknown[]) => void) => () => void;
}

// Expose API to renderer
const api: AiosDesktopAPI = {
  window: {
    minimize: () => ipcRenderer.invoke("window:minimize"),
    maximize: () => ipcRenderer.invoke("window:maximize"),
    close: () => ipcRenderer.invoke("window:close"),
    focus: () => ipcRenderer.invoke("window:focus"),
    isVisible: () => ipcRenderer.invoke("window:isVisible"),
  },

  app: {
    version: () => ipcRenderer.invoke("app:version"),
    name: () => ipcRenderer.invoke("app:name"),
    platform: () => ipcRenderer.invoke("app:platform"),
    isPackaged: () => ipcRenderer.invoke("app:isPackaged"),
  },

  system: {
    screenSize: () => ipcRenderer.invoke("system:screen-size"),
    openExternal: (url: string) => ipcRenderer.invoke("system:open-external", url),
    showItemInFolder: (fullPath: string) => ipcRenderer.invoke("system:show-item-in-folder", fullPath),
  },

  dialog: {
    openFile: (options?: Electron.OpenDialogOptions) => ipcRenderer.invoke("dialog:open-file", options),
    saveFile: (options?: Electron.SaveDialogOptions) => ipcRenderer.invoke("dialog:save-file", options),
  },

  store: {
    get: <T = unknown>(key: string) => ipcRenderer.invoke("store:get", key) as Promise<T>,
    set: (key: string, value: unknown) => ipcRenderer.invoke("store:set", key, value),
    delete: (key: string) => ipcRenderer.invoke("store:delete", key),
    clear: () => ipcRenderer.invoke("store:clear"),
  },

  notification: {
    send: (options: { title: string; body: string }) => ipcRenderer.invoke("notification:send", options),
  },

  update: {
    check: () => ipcRenderer.invoke("update:check"),
    install: () => ipcRenderer.invoke("update:install"),
    status: () => ipcRenderer.invoke("update:status"),
    on: (channel: string, callback: (...args: unknown[]) => void) => {
      const validChannels = [
        "update:checking",
        "update:available",
        "update:not-available",
        "update:progress",
        "update:downloaded",
        "update:error",
      ];
      if (validChannels.includes(channel)) {
        const handler = (_event: Electron.IpcRendererEvent, ...args: unknown[]) => callback(...args);
        ipcRenderer.on(channel, handler);
        return () => {
          ipcRenderer.removeListener(channel, handler);
        };
      }
      return () => {};
    },
  },

  navigate: (workspaceId: string) => ipcRenderer.invoke("navigate", workspaceId),

  deepLink: {
    register: () => ipcRenderer.invoke("deep-link:register"),
    on: (callback: (data: { path: string; params: URLSearchParams }) => void) => {
      const handler = (_event: Electron.IpcRendererEvent, data: { path: string; params: Record<string, string> }) => {
        const params = new URLSearchParams(data.params);
        callback({ path: data.path, params });
      };
      ipcRenderer.on("deep-link", handler);
      return () => {
        ipcRenderer.removeListener("deep-link", handler);
      };
    },
  },

  on: (channel: string, callback: (...args: unknown[]) => void) => {
    const validChannels = [
      "navigate",
      "deep-link",
      "check-for-updates",
      "update:checking",
      "update:available",
      "update:not-available",
      "update:progress",
      "update:downloaded",
      "update:error",
      "command-palette:toggle",
      "sidebar:toggle",
      "file:opened",
      "power-event",
      "plugin-loaded",
      "plugin-activated",
      "plugin-deactivated",
      "plugin-unloaded",
      "plugin-enabled",
      "plugin-disabled",
      "sync-complete",
      "sync-error",
      "workspace-created",
      "collaborator-added",
      "activity",
      "typing-started",
      "typing-stopped",
    ];
    if (validChannels.includes(channel)) {
      const handler = (_event: Electron.IpcRendererEvent, ...args: unknown[]) => callback(...args);
      ipcRenderer.on(channel, handler);
      return () => {
        ipcRenderer.removeListener(channel, handler);
      };
    }
    return () => {};
  },

  // --- M13: Shortcuts ---
  shortcuts: {
    list: () => ipcRenderer.invoke("shortcuts:list"),
    update: (id: string, accelerator: string) => ipcRenderer.invoke("shortcuts:update", id, accelerator),
    setEnabled: (id: string, enabled: boolean) => ipcRenderer.invoke("shortcuts:set-enabled", id, enabled),
  },

  // --- M13: Clipboard ---
  clipboard: {
    read: () => ipcRenderer.invoke("clipboard:read"),
    writeText: (text: string) => ipcRenderer.invoke("clipboard:write-text", text),
    writeHTML: (html: string) => ipcRenderer.invoke("clipboard:write-html", html),
    clear: () => ipcRenderer.invoke("clipboard:clear"),
    hasText: () => ipcRenderer.invoke("clipboard:has-text"),
  },

  // --- M13: Auto-launch ---
  autoLaunch: {
    isEnabled: () => ipcRenderer.invoke("auto-launch:isEnabled"),
    setEnabled: (enabled: boolean) => ipcRenderer.invoke("auto-launch:setEnabled", enabled),
    toggle: () => ipcRenderer.invoke("auto-launch:toggle"),
  },

  // --- M13: Power monitor ---
  power: {
    state: () => ipcRenderer.invoke("power:state"),
  },

  // --- M14: Developer Console ---
  devconsole: {
    logs: (filter?: { level?: string; source?: string; search?: string }) =>
      ipcRenderer.invoke("devconsole:logs", filter),
    clearLogs: () => ipcRenderer.invoke("devconsole:clear-logs"),
    diagnostics: () => ipcRenderer.invoke("devconsole:diagnostics"),
    performance: () => ipcRenderer.invoke("devconsole:performance"),
    toggleDevTools: () => ipcRenderer.invoke("devconsole:toggle-devtools"),
    openDevTools: () => ipcRenderer.invoke("devconsole:open-devtools"),
    closeDevTools: () => ipcRenderer.invoke("devconsole:close-devtools"),
    isDevToolsOpen: () => ipcRenderer.invoke("devconsole:is-devtools-open"),
    startCapture: () => ipcRenderer.invoke("devconsole:start-capture"),
    stopCapture: () => ipcRenderer.invoke("devconsole:stop-capture"),
    isCapturing: () => ipcRenderer.invoke("devconsole:is-capturing"),
  },

  // --- M14: Plugin System ---
  plugins: {
    list: () => ipcRenderer.invoke("plugins:list"),
    scan: () => ipcRenderer.invoke("plugins:scan"),
    load: (name: string) => ipcRenderer.invoke("plugins:load", name),
    activate: (name: string) => ipcRenderer.invoke("plugins:activate", name),
    deactivate: (name: string) => ipcRenderer.invoke("plugins:deactivate", name),
    unload: (name: string) => ipcRenderer.invoke("plugins:unload", name),
    enable: (name: string) => ipcRenderer.invoke("plugins:enable", name),
    disable: (name: string) => ipcRenderer.invoke("plugins:disable", name),
    isLoaded: (name: string) => ipcRenderer.invoke("plugins:is-loaded", name),
    getDir: () => ipcRenderer.invoke("plugins:dir"),
  },

  // --- M14: Advanced Window Management ---
  windows: {
    create: (config: any) => ipcRenderer.invoke("windows:create", config),
    close: (id: string) => ipcRenderer.invoke("windows:close", id),
    focus: (id: string) => ipcRenderer.invoke("windows:focus", id),
    minimize: (id: string) => ipcRenderer.invoke("windows:minimize", id),
    maximize: (id: string) => ipcRenderer.invoke("windows:maximize", id),
    getAllStates: () => ipcRenderer.invoke("windows:all-states"),
    getState: (id: string) => ipcRenderer.invoke("windows:state", id),
    tile: (ids: string[], direction?: string) => ipcRenderer.invoke("windows:tile", ids, direction),
    cascade: (ids?: string[]) => ipcRenderer.invoke("windows:cascade", ids),
    getGroup: (groupId: string) => ipcRenderer.invoke("windows:get-group", groupId),
    closeGroup: (groupId: string) => ipcRenderer.invoke("windows:close-group", groupId),
  },

  // --- M14: System Integration ---
  systemBadge: {
    set: (options: { count?: number; text?: string; color?: string }) =>
      ipcRenderer.invoke("system:set-badge", options),
    clear: () => ipcRenderer.invoke("system:clear-badge"),
    getState: () => ipcRenderer.invoke("system:badge-state"),
  },
  systemProgress: {
    set: (options: { progress: number; mode?: string }) =>
      ipcRenderer.invoke("system:set-progress", options),
    clear: () => ipcRenderer.invoke("system:clear-progress"),
    getState: () => ipcRenderer.invoke("system:progress-state"),
  },
  systemOverlay: {
    set: (iconPath: string, description: string) =>
      ipcRenderer.invoke("system:set-overlay", iconPath, description),
    clear: () => ipcRenderer.invoke("system:clear-overlay"),
  },
  systemFlash: {
    frame: (flash: boolean) => ipcRenderer.invoke("system:flash-frame", flash),
  },
  systemTooltip: {
    set: (text: string) => ipcRenderer.invoke("system:set-tooltip", text),
  },

  // --- M15: Cloud Sync ---
  sync: {
    state: () => ipcRenderer.invoke("sync:state"),
    setItem: (type: string, key: string, data: unknown) =>
      ipcRenderer.invoke("sync:set-item", type, key, data),
    getItem: (type: string, key: string) => ipcRenderer.invoke("sync:get-item", type, key),
    removeItem: (type: string, key: string) => ipcRenderer.invoke("sync:remove-item", type, key),
    forceSync: () => ipcRenderer.invoke("sync:force-sync"),
    setEnabled: (enabled: boolean) => ipcRenderer.invoke("sync:set-enabled", enabled),
    conflicts: () => ipcRenderer.invoke("sync:conflicts"),
    resolveConflict: (itemId: string, resolution: string) =>
      ipcRenderer.invoke("sync:resolve-conflict", itemId, resolution),
  },

  // --- M15: Collaboration ---
  collab: {
    createWorkspace: (name: string, isPublic?: boolean) =>
      ipcRenderer.invoke("collab:create-workspace", name, isPublic),
    getWorkspaces: () => ipcRenderer.invoke("collab:get-workspaces"),
    getWorkspace: (id: string) => ipcRenderer.invoke("collab:get-workspace", id),
    deleteWorkspace: (id: string) => ipcRenderer.invoke("collab:delete-workspace", id),
    setActive: (id: string | null) => ipcRenderer.invoke("collab:set-active", id),
    addCollaborator: (wsId: string, collaborator: any) =>
      ipcRenderer.invoke("collab:add-collaborator", wsId, collaborator),
    removeCollaborator: (wsId: string, userId: string) =>
      ipcRenderer.invoke("collab:remove-collaborator", wsId, userId),
    updateCursor: (userId: string, position: any) =>
      ipcRenderer.invoke("collab:update-cursor", userId, position),
    activeCollaborators: () => ipcRenderer.invoke("collab:active-collaborators"),
    activity: (limit?: number) => ipcRenderer.invoke("collab:activity", limit),
    state: () => ipcRenderer.invoke("collab:state"),
  },

  // --- M15: Analytics ---
  analytics: {
    state: () => ipcRenderer.invoke("analytics:state"),
    startSession: (feature: string, action: string) =>
      ipcRenderer.invoke("analytics:start-session", feature, action),
    endSession: () => ipcRenderer.invoke("analytics:end-session"),
    trackEvent: (feature: string, action: string) =>
      ipcRenderer.invoke("analytics:track-event", feature, action),
    featureUsage: () => ipcRenderer.invoke("analytics:feature-usage"),
    productivity: () => ipcRenderer.invoke("analytics:productivity"),
    sessions: (limit?: number) => ipcRenderer.invoke("analytics:sessions", limit),
  },

  // --- M15: AI Assistant ---
  ai: {
    state: () => ipcRenderer.invoke("ai:state"),
    sendMessage: (content: string, context?: any) =>
      ipcRenderer.invoke("ai:send-message", content, context),
    createConversation: (title?: string) => ipcRenderer.invoke("ai:create-conversation", title),
    getConversations: () => ipcRenderer.invoke("ai:get-conversations"),
    setActiveConversation: (id: string | null) =>
      ipcRenderer.invoke("ai:set-active-conversation", id),
    deleteConversation: (id: string) => ipcRenderer.invoke("ai:delete-conversation", id),
    updateContext: (context: any) => ipcRenderer.invoke("ai:update-context", context),
    commandHistory: () => ipcRenderer.invoke("ai:command-history"),
  },

  // --- M16: Supervisor (Goal Manager) ---
  supervisor: {
    state: () => ipcRenderer.invoke("supervisor:state"),
    submitGoal: (goal: any) => ipcRenderer.invoke("supervisor:submit-goal", goal),
    getGoal: (goalId: string) => ipcRenderer.invoke("supervisor:get-goal", goalId),
    cancelGoal: (goalId: string) => ipcRenderer.invoke("supervisor:cancel-goal", goalId),
    pauseGoal: (goalId: string) => ipcRenderer.invoke("supervisor:pause-goal", goalId),
    resumeGoal: (goalId: string) => ipcRenderer.invoke("supervisor:resume-goal", goalId),
    tick: () => ipcRenderer.invoke("supervisor:tick"),
  },

  // --- M16: Planner ---
  planner: {
    plan: (goalId: string, goalDescription: string) =>
      ipcRenderer.invoke("planner:plan", goalId, goalDescription),
    getPlan: (goalId: string) => ipcRenderer.invoke("planner:get-plan", goalId),
    replan: (goalId: string, failureTaskId: string) =>
      ipcRenderer.invoke("planner:replan", goalId, failureTaskId),
    completeTask: (goalId: string, taskId: string, output?: any) =>
      ipcRenderer.invoke("planner:complete-task", goalId, taskId, output),
    failTask: (goalId: string, taskId: string) =>
      ipcRenderer.invoke("planner:fail-task", goalId, taskId),
    executeReady: (goalId: string) => ipcRenderer.invoke("planner:execute-ready", goalId),
    getCriticalPath: (goalId: string) => ipcRenderer.invoke("planner:get-critical-path", goalId),
  },

  // --- M16: Agent Runtime ---
  runtime: {
    state: () => ipcRenderer.invoke("runtime:state"),
    execute: (agentName: string, task: any, sharedCtx?: any) =>
      ipcRenderer.invoke("runtime:execute", agentName, task, sharedCtx),
    executeParallel: (agentNames: string[], task: any) =>
      ipcRenderer.invoke("runtime:execute-parallel", agentNames, task),
    message: (from: string, to: string, message: any) =>
      ipcRenderer.invoke("runtime:message", from, to, message),
    inbox: (agentName: string) => ipcRenderer.invoke("runtime:inbox", agentName),
    context: (agentName: string) => ipcRenderer.invoke("runtime:context", agentName),
    setContext: (agentName: string, key: string, value: any) =>
      ipcRenderer.invoke("runtime:set-context", agentName, key, value),
    artifacts: (agentName: string) => ipcRenderer.invoke("runtime:artifacts", agentName),
    agents: () => ipcRenderer.invoke("runtime:agents"),
  },

  // --- M16: Desktop Automation ---
  automation: {
    mouseClick: (options: any) => ipcRenderer.invoke("automation:mouse-click", options),
    mouseMove: (x: number, y: number, duration?: number) =>
      ipcRenderer.invoke("automation:mouse-move", x, y, duration),
    mouseDrag: (fromX: number, fromY: number, toX: number, toY: number, duration?: number) =>
      ipcRenderer.invoke("automation:mouse-drag", fromX, fromY, toX, toY, duration),
    mouseScroll: (deltaX: number, deltaY: number) =>
      ipcRenderer.invoke("automation:mouse-scroll", deltaX, deltaY),
    keyboardType: (text: string, delay?: number) =>
      ipcRenderer.invoke("automation:keyboard-type", text, delay),
    keyboardHotkey: (keys: string[]) => ipcRenderer.invoke("automation:keyboard-hotkey", keys),
    keyboardSequence: (steps: any[]) => ipcRenderer.invoke("automation:keyboard-sequence", steps),
    screenshot: (region?: any) => ipcRenderer.invoke("automation:screenshot", region),
    windows: () => ipcRenderer.invoke("automation:windows"),
    focusWindow: (windowTitle: string) =>
      ipcRenderer.invoke("automation:focus-window", windowTitle),
    closeWindow: (windowTitle: string) =>
      ipcRenderer.invoke("automation:close-window", windowTitle),
    clipboardRead: () => ipcRenderer.invoke("automation:clipboard-read"),
    clipboardWrite: (text: string) => ipcRenderer.invoke("automation:clipboard-write", text),
    ocr: (imagePath: string) => ipcRenderer.invoke("automation:ocr", imagePath),
    accessibilityTree: () => ipcRenderer.invoke("automation:accessibility-tree"),
  },

  // --- M16: Workflow Engine ---
  workflow: {
    state: () => ipcRenderer.invoke("workflow:state"),
    create: (workflow: any) => ipcRenderer.invoke("workflow:create", workflow),
    get: (workflowId: string) => ipcRenderer.invoke("workflow:get", workflowId),
    delete: (workflowId: string) => ipcRenderer.invoke("workflow:delete", workflowId),
    enable: (workflowId: string) => ipcRenderer.invoke("workflow:enable", workflowId),
    disable: (workflowId: string) => ipcRenderer.invoke("workflow:disable", workflowId),
    execute: (workflowId: string, data?: any) =>
      ipcRenderer.invoke("workflow:execute", workflowId, data),
    tick: () => ipcRenderer.invoke("workflow:tick"),
    active: () => ipcRenderer.invoke("workflow:active"),
    history: (workflowId?: string) => ipcRenderer.invoke("workflow:history", workflowId),
  },

  // --- M16: Observability ---
  obs: {
    state: () => ipcRenderer.invoke("obs:state"),
    executionGraph: () => ipcRenderer.invoke("obs:execution-graph"),
    goalTimeline: (goalId: string) => ipcRenderer.invoke("obs:goal-timeline", goalId),
    costSummary: () => ipcRenderer.invoke("obs:cost-summary"),
    recordExecution: (event: any) => ipcRenderer.invoke("obs:record-execution", event),
    performanceMetrics: () => ipcRenderer.invoke("obs:performance-metrics"),
    liveStream: () => ipcRenderer.invoke("obs:live-stream"),
  },

  // --- M16: Persistence ---
  persistence: {
    state: () => ipcRenderer.invoke("persistence:state"),
    createCheckpoint: (checkpoint: any) =>
      ipcRenderer.invoke("persistence:create-checkpoint", checkpoint),
    getCheckpoint: (id: string) => ipcRenderer.invoke("persistence:get-checkpoint", id),
    restoreCheckpoint: (id: string) => ipcRenderer.invoke("persistence:restore-checkpoint", id),
    listCheckpoints: (goalId?: string) => ipcRenderer.invoke("persistence:list-checkpoints", goalId),
    enqueue: (queue: string, item: any) => ipcRenderer.invoke("persistence:enqueue", queue, item),
    dequeue: (queue: string) => ipcRenderer.invoke("persistence:dequeue", queue),
    peekQueue: (queue: string) => ipcRenderer.invoke("persistence:peek-queue", queue),
    recordHistory: (entry: any) => ipcRenderer.invoke("persistence:record-history", entry),
    history: (filters?: any) => ipcRenderer.invoke("persistence:history", filters),
    export: () => ipcRenderer.invoke("persistence:export"),
    import: (data: any) => ipcRenderer.invoke("persistence:import", data),
    stateVersions: (key: string) => ipcRenderer.invoke("persistence:state-versions", key),
    restoreVersion: (key: string, version: number) =>
      ipcRenderer.invoke("persistence:restore-version", key, version),
    cleanup: (maxHistory?: number) => ipcRenderer.invoke("persistence:cleanup", maxHistory),
  },
};

// Expose to window
contextBridge.exposeInMainWorld("aios", api);

// Log readiness
console.log("[AIOS] Preload script loaded");
