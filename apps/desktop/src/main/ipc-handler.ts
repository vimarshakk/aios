/**
 * IpcHandler — IPC bridge between main and renderer processes.
 *
 * Exposes safe, typed APIs to the renderer via preload script.
 * All communication goes through ipcMain.handle() / ipcRenderer.invoke().
 */

import { ipcMain, BrowserWindow, app, shell, dialog, screen } from "electron";
import { WindowManager } from "./window-manager";
import { StoreManager } from "./store-manager";
import { NotificationManager } from "./notification-manager";
import { UpdateManager } from "./update-manager";
import { ShortcutsManager } from "./shortcuts-manager";
import { ClipboardManager } from "./clipboard-manager";
import { AutoLaunchManager } from "./auto-launch-manager";
import { PowerMonitorManager } from "./power-monitor-manager";
import { FileAssociationManager } from "./file-association-manager";
import { DeveloperConsole } from "./developer-console";
import { PluginManager } from "./plugin-manager";
import { AdvancedWindowManager } from "./advanced-window-manager";
import { SystemIntegration } from "./system-integration";
import { CloudSync } from "./cloud-sync";
import { CollaborationManager } from "./collaboration-manager";
import { AnalyticsEngine } from "./analytics-engine";
import { AIAssistant } from "./ai-assistant";
import { Supervisor } from "./supervisor";
import { Planner } from "./planner";
import { AgentRuntime } from "./agent-runtime";
import { DesktopAutomation } from "./desktop-automation";
import { WorkflowEngine } from "./workflow-engine";
import { Observability } from "./observability";
import { Persistence } from "./persistence";
import { WorkforceManager } from "./workforce-manager";
import { CLIController } from "./cli-controller";
import { ReviewPipeline } from "./review-pipeline";

export interface IpcHandlerDeps {
  windowManager: WindowManager;
  storeManager: StoreManager;
  notificationManager: NotificationManager;
  updateManager: UpdateManager;
  shortcutsManager: ShortcutsManager;
  clipboardManager: ClipboardManager;
  autoLaunchManager: AutoLaunchManager;
  powerMonitorManager: PowerMonitorManager;
  fileAssociationManager: FileAssociationManager;
  developerConsole: DeveloperConsole;
  pluginManager: PluginManager;
  advancedWindowManager: AdvancedWindowManager;
  systemIntegration: SystemIntegration;
  cloudSync: CloudSync;
  collaborationManager: CollaborationManager;
  analyticsEngine: AnalyticsEngine;
  aiAssistant: AIAssistant;
  supervisor: Supervisor;
  planner: Planner;
  agentRuntime: AgentRuntime;
  desktopAutomation: DesktopAutomation;
  workflowEngine: WorkflowEngine;
  observability: Observability;
  persistence: Persistence;
  workforceManager: WorkforceManager;
  cliController: CLIController;
  reviewPipeline: ReviewPipeline;
}

export class IpcHandler {
  private deps: IpcHandlerDeps;

  constructor(deps: IpcHandlerDeps) {
    this.deps = deps;
  }

  register() {
    // --- Window management ---
    ipcMain.handle("window:minimize", () => this.deps.windowManager.minimize());
    ipcMain.handle("window:maximize", () => this.deps.windowManager.maximize());
    ipcMain.handle("window:close", () => this.deps.windowManager.close());
    ipcMain.handle("window:focus", () => this.deps.windowManager.focus());
    ipcMain.handle("window:isVisible", () => this.deps.windowManager.isVisible());

    // --- App info ---
    ipcMain.handle("app:version", () => app.getVersion());
    ipcMain.handle("app:name", () => app.getName());
    ipcMain.handle("app:platform", () => process.platform);
    ipcMain.handle("app:isPackaged", () => app.isPackaged);

    // --- System ---
    ipcMain.handle("system:screen-size", () => {
      const display = screen.getPrimaryDisplay();
      return display.workAreaSize;
    });
    ipcMain.handle("system:open-external", (_event, url: string) => {
      if (url.startsWith("http")) {
        shell.openExternal(url);
      }
    });
    ipcMain.handle("system:show-item-in-folder", (_event, fullPath: string) => {
      shell.showItemInFolder(fullPath);
    });

    // --- Dialog ---
    ipcMain.handle("dialog:open-file", async (_event, options?: Electron.OpenDialogOptions) => {
      const result = await dialog.showOpenDialog(options ?? { properties: ["openFile"] });
      return result.canceled ? null : result.filePaths;
    });
    ipcMain.handle("dialog:save-file", async (_event, options?: Electron.SaveDialogOptions) => {
      const result = await dialog.showSaveDialog(options ?? {});
      return result.canceled ? null : result.filePath;
    });

    // --- Store (persistent settings) ---
    ipcMain.handle("store:get", (_event, key: string) => {
      return this.deps.storeManager.get(key);
    });
    ipcMain.handle("store:set", (_event, key: string, value: unknown) => {
      this.deps.storeManager.set(key, value);
    });
    ipcMain.handle("store:delete", (_event, key: string) => {
      this.deps.storeManager.delete(key);
    });
    ipcMain.handle("store:clear", () => {
      this.deps.storeManager.clear();
    });

    // --- Notifications ---
    ipcMain.handle("notification:send", (_event, options: { title: string; body: string }) => {
      const mainWindow = this.deps.windowManager.getMainWindow();
      this.deps.notificationManager.send(options, mainWindow);
    });

    // --- Update ---
    ipcMain.handle("update:check", () => {
      this.deps.updateManager.checkForUpdates();
    });
    ipcMain.handle("update:install", () => {
      this.deps.updateManager.quitAndInstall();
    });
    ipcMain.handle("update:status", () => {
      return this.deps.updateManager.getStatus();
    });

    // --- Navigation ---
    ipcMain.handle("navigate", (_event, workspaceId: string) => {
      const mainWindow = this.deps.windowManager.getMainWindow();
      mainWindow?.webContents.send("navigate", workspaceId);
    });

    // --- Deep link ---
    ipcMain.handle("deep-link:register", () => {
      // Already registered in main index
      return true;
    });

    // --- M13: Shortcuts ---
    ipcMain.handle("shortcuts:list", () => {
      return this.deps.shortcutsManager.getAll();
    });
    ipcMain.handle("shortcuts:update", (_event, id: string, accelerator: string) => {
      this.deps.shortcutsManager.updateAccelerator(id, accelerator);
    });
    ipcMain.handle("shortcuts:set-enabled", (_event, id: string, enabled: boolean) => {
      this.deps.shortcutsManager.setEnabled(id, enabled);
    });

    // --- M13: Clipboard ---
    ipcMain.handle("clipboard:read", () => {
      return this.deps.clipboardManager.read();
    });
    ipcMain.handle("clipboard:write-text", (_event, text: string) => {
      this.deps.clipboardManager.writeText(text);
    });
    ipcMain.handle("clipboard:write-html", (_event, html: string) => {
      this.deps.clipboardManager.writeHTML(html);
    });
    ipcMain.handle("clipboard:clear", () => {
      this.deps.clipboardManager.clear();
    });
    ipcMain.handle("clipboard:has-text", () => {
      return this.deps.clipboardManager.hasText();
    });

    // --- M13: Auto-launch ---
    ipcMain.handle("auto-launch:isEnabled", () => {
      return this.deps.autoLaunchManager.isEnabled();
    });
    ipcMain.handle("auto-launch:setEnabled", (_event, enabled: boolean) => {
      this.deps.autoLaunchManager.setEnabled(enabled);
    });
    ipcMain.handle("auto-launch:toggle", () => {
      return this.deps.autoLaunchManager.toggle();
    });

    // --- M13: Power monitor ---
    ipcMain.handle("power:state", () => {
      return this.deps.powerMonitorManager.getState();
    });

    // --- M13: File association ---
    ipcMain.handle("file:supported-types", () => {
      return this.deps.fileAssociationManager.getSupportedFileTypes();
    });

    // --- M14: Developer Console ---
    ipcMain.handle("devconsole:logs", (_event, filter?) => {
      return this.deps.developerConsole.getLogs(filter);
    });
    ipcMain.handle("devconsole:clear-logs", () => {
      this.deps.developerConsole.clearLogs();
    });
    ipcMain.handle("devconsole:diagnostics", () => {
      return this.deps.developerConsole.getDiagnostics();
    });
    ipcMain.handle("devconsole:performance", () => {
      return this.deps.developerConsole.getPerformanceMetrics();
    });
    ipcMain.handle("devconsole:toggle-devtools", () => {
      const win = this.deps.windowManager.getMainWindow();
      this.deps.developerConsole.toggleDevTools(win);
    });
    ipcMain.handle("devconsole:open-devtools", () => {
      const win = this.deps.windowManager.getMainWindow();
      this.deps.developerConsole.openDevTools(win);
    });
    ipcMain.handle("devconsole:close-devtools", () => {
      const win = this.deps.windowManager.getMainWindow();
      this.deps.developerConsole.closeDevTools(win);
    });
    ipcMain.handle("devconsole:is-devtools-open", () => {
      const win = this.deps.windowManager.getMainWindow();
      return this.deps.developerConsole.isDevToolsOpen(win);
    });
    ipcMain.handle("devconsole:start-capture", () => {
      this.deps.developerConsole.startCapture();
    });
    ipcMain.handle("devconsole:stop-capture", () => {
      this.deps.developerConsole.stopCapture();
    });
    ipcMain.handle("devconsole:is-capturing", () => {
      return this.deps.developerConsole["captureEnabled"];
    });

    // --- M14: Plugin System ---
    ipcMain.handle("plugins:list", () => {
      return this.deps.pluginManager.getPlugins();
    });
    ipcMain.handle("plugins:scan", () => {
      return this.deps.pluginManager.scanPlugins();
    });
    ipcMain.handle("plugins:load", (_event, name: string) => {
      return this.deps.pluginManager.loadPlugin(name);
    });
    ipcMain.handle("plugins:activate", async (_event, name: string) => {
      return await this.deps.pluginManager.activatePlugin(name);
    });
    ipcMain.handle("plugins:deactivate", async (_event, name: string) => {
      return await this.deps.pluginManager.deactivatePlugin(name);
    });
    ipcMain.handle("plugins:unload", async (_event, name: string) => {
      return await this.deps.pluginManager.unloadPlugin(name);
    });
    ipcMain.handle("plugins:enable", (_event, name: string) => {
      return this.deps.pluginManager.enablePlugin(name);
    });
    ipcMain.handle("plugins:disable", (_event, name: string) => {
      return this.deps.pluginManager.disablePlugin(name);
    });
    ipcMain.handle("plugins:is-loaded", (_event, name: string) => {
      return this.deps.pluginManager.isPluginLoaded(name);
    });
    ipcMain.handle("plugins:dir", () => {
      return this.deps.pluginManager.getPluginsDir();
    });

    // --- M14: Advanced Window Management ---
    ipcMain.handle("windows:create", (_event, config) => {
      return this.deps.advancedWindowManager.createWindow(config) !== null;
    });
    ipcMain.handle("windows:close", (_event, id: string) => {
      return this.deps.advancedWindowManager.closeWindow(id);
    });
    ipcMain.handle("windows:focus", (_event, id: string) => {
      return this.deps.advancedWindowManager.focusWindow(id);
    });
    ipcMain.handle("windows:minimize", (_event, id: string) => {
      return this.deps.advancedWindowManager.minimizeWindow(id);
    });
    ipcMain.handle("windows:maximize", (_event, id: string) => {
      return this.deps.advancedWindowManager.maximizeWindow(id);
    });
    ipcMain.handle("windows:all-states", () => {
      return this.deps.advancedWindowManager.getAllWindowStates();
    });
    ipcMain.handle("windows:state", (_event, id: string) => {
      return this.deps.advancedWindowManager.getWindowState(id);
    });
    ipcMain.handle("windows:tile", (_event, ids: string[], direction?: string) => {
      return this.deps.advancedWindowManager.tileWindows(ids, direction as any);
    });
    ipcMain.handle("windows:cascade", (_event, ids?: string[]) => {
      return this.deps.advancedWindowManager.cascadeWindows(ids);
    });
    ipcMain.handle("windows:get-group", (_event, groupId: string) => {
      return this.deps.advancedWindowManager.getGroup(groupId);
    });
    ipcMain.handle("windows:close-group", (_event, groupId: string) => {
      this.deps.advancedWindowManager.closeGroup(groupId);
    });

    // --- M14: System Integration ---
    ipcMain.handle("system:set-badge", (_event, options) => {
      this.deps.systemIntegration.updateBadge(options);
    });
    ipcMain.handle("system:clear-badge", () => {
      this.deps.systemIntegration.clearBadge();
    });
    ipcMain.handle("system:set-progress", (_event, options) => {
      const win = this.deps.windowManager.getMainWindow();
      this.deps.systemIntegration.setProgress(options, win);
    });
    ipcMain.handle("system:clear-progress", () => {
      const win = this.deps.windowManager.getMainWindow();
      this.deps.systemIntegration.clearProgress(win);
    });
    ipcMain.handle("system:set-overlay", (_event, iconPath: string, description: string) => {
      const win = this.deps.windowManager.getMainWindow();
      this.deps.systemIntegration.setOverlayIcon(iconPath, description, win);
    });
    ipcMain.handle("system:clear-overlay", () => {
      const win = this.deps.windowManager.getMainWindow();
      this.deps.systemIntegration.clearOverlayIcon(win);
    });
    ipcMain.handle("system:flash-frame", (_event, flash: boolean) => {
      const win = this.deps.windowManager.getMainWindow();
      this.deps.systemIntegration.flashFrame(flash, win);
    });
    ipcMain.handle("system:set-tooltip", (_event, text: string) => {
      this.deps.systemIntegration.setToolTip(text);
    });
    ipcMain.handle("system:badge-state", () => {
      return this.deps.systemIntegration.getBadgeState();
    });
    ipcMain.handle("system:progress-state", () => {
      return this.deps.systemIntegration.getProgressState();
    });

    // --- M15: Cloud Sync ---
    ipcMain.handle("sync:state", () => {
      return this.deps.cloudSync.getState();
    });
    ipcMain.handle("sync:set-item", (_event, type: string, key: string, data: unknown) => {
      return this.deps.cloudSync.setItem(type as any, key, data);
    });
    ipcMain.handle("sync:get-item", (_event, type: string, key: string) => {
      return this.deps.cloudSync.getItem(type as any, key);
    });
    ipcMain.handle("sync:remove-item", (_event, type: string, key: string) => {
      return this.deps.cloudSync.removeItem(type as any, key);
    });
    ipcMain.handle("sync:force-sync", async () => {
      return await this.deps.cloudSync.forceSyncAll();
    });
    ipcMain.handle("sync:set-enabled", (_event, enabled: boolean) => {
      this.deps.cloudSync.setEnabled(enabled);
    });
    ipcMain.handle("sync:conflicts", () => {
      return this.deps.cloudSync.getConflicts();
    });
    ipcMain.handle("sync:resolve-conflict", (_event, itemId: string, resolution: string) => {
      return this.deps.cloudSync.resolveConflict(itemId, resolution as any);
    });

    // --- M15: Collaboration ---
    ipcMain.handle("collab:create-workspace", (_event, name: string, isPublic?: boolean) => {
      return this.deps.collaborationManager.createWorkspace(name, isPublic);
    });
    ipcMain.handle("collab:get-workspaces", () => {
      return this.deps.collaborationManager.getWorkspaces();
    });
    ipcMain.handle("collab:get-workspace", (_event, id: string) => {
      return this.deps.collaborationManager.getWorkspace(id);
    });
    ipcMain.handle("collab:delete-workspace", (_event, id: string) => {
      return this.deps.collaborationManager.deleteWorkspace(id);
    });
    ipcMain.handle("collab:set-active", (_event, id: string | null) => {
      this.deps.collaborationManager.setActiveWorkspace(id);
    });
    ipcMain.handle("collab:add-collaborator", (_event, wsId: string, collaborator: any) => {
      return this.deps.collaborationManager.addCollaborator(wsId, collaborator);
    });
    ipcMain.handle("collab:remove-collaborator", (_event, wsId: string, userId: string) => {
      return this.deps.collaborationManager.removeCollaborator(wsId, userId);
    });
    ipcMain.handle("collab:update-cursor", (_event, userId: string, position: any) => {
      this.deps.collaborationManager.updateCursor(userId, position);
    });
    ipcMain.handle("collab:active-collaborators", () => {
      return this.deps.collaborationManager.getActiveCollaborators();
    });
    ipcMain.handle("collab:activity", (_event, limit?: number) => {
      return this.deps.collaborationManager.getActivityFeed(limit);
    });
    ipcMain.handle("collab:state", () => {
      return this.deps.collaborationManager.getState();
    });

    // --- M15: Analytics ---
    ipcMain.handle("analytics:state", () => {
      return this.deps.analyticsEngine.getSnapshot();
    });
    ipcMain.handle("analytics:start-session", (_event, feature: string, action: string) => {
      return this.deps.analyticsEngine.startSession(feature, action);
    });
    ipcMain.handle("analytics:end-session", () => {
      return this.deps.analyticsEngine.endSession();
    });
    ipcMain.handle("analytics:track-event", (_event, feature: string, action: string) => {
      this.deps.analyticsEngine.trackEvent(feature, action);
    });
    ipcMain.handle("analytics:feature-usage", () => {
      return this.deps.analyticsEngine.getFeatureUsage();
    });
    ipcMain.handle("analytics:productivity", () => {
      return this.deps.analyticsEngine.getProductivityScore();
    });
    ipcMain.handle("analytics:sessions", (_event, limit?: number) => {
      return this.deps.analyticsEngine.getSessions(limit);
    });

    // --- M15: AI Assistant ---
    ipcMain.handle("ai:state", () => {
      return this.deps.aiAssistant.getState();
    });
    ipcMain.handle("ai:send-message", async (_event, content: string, context?: any) => {
      return await this.deps.aiAssistant.sendMessage(content, context);
    });
    ipcMain.handle("ai:create-conversation", (_event, title?: string) => {
      return this.deps.aiAssistant.createConversation(title);
    });
    ipcMain.handle("ai:get-conversations", () => {
      return this.deps.aiAssistant.getConversations();
    });
    ipcMain.handle("ai:set-active-conversation", (_event, id: string | null) => {
      this.deps.aiAssistant.setActiveConversation(id);
    });
    ipcMain.handle("ai:delete-conversation", (_event, id: string) => {
      return this.deps.aiAssistant.deleteConversation(id);
    });
    ipcMain.handle("ai:update-context", (_event, context: any) => {
      this.deps.aiAssistant.updateContext(context);
    });
    ipcMain.handle("ai:command-history", () => {
      return this.deps.aiAssistant.getCommandHistory();
    });

    // --- M16: Supervisor (Goal Manager) ---
    ipcMain.handle("supervisor:state", () => {
      return this.deps.supervisor.getState();
    });
    ipcMain.handle("supervisor:submit-goal", (_event, goal: any) => {
      return this.deps.supervisor.submitGoal(goal);
    });
    ipcMain.handle("supervisor:get-goal", (_event, goalId: string) => {
      return this.deps.supervisor.getGoal(goalId);
    });
    ipcMain.handle("supervisor:cancel-goal", (_event, goalId: string) => {
      this.deps.supervisor.cancelGoal(goalId);
    });
    ipcMain.handle("supervisor:pause-goal", (_event, goalId: string) => {
      this.deps.supervisor.pauseGoal(goalId);
    });
    ipcMain.handle("supervisor:resume-goal", (_event, goalId: string) => {
      this.deps.supervisor.resumeGoal(goalId);
    });
    ipcMain.handle("supervisor:tick", async () => {
      await this.deps.supervisor.tick();
    });

    // --- M16: Planner ---
    ipcMain.handle("planner:plan", (_event, goalId: string, goalDescription: string) => {
      return this.deps.planner.plan(goalId, goalDescription);
    });
    ipcMain.handle("planner:get-plan", (_event, goalId: string) => {
      return this.deps.planner.getPlan(goalId);
    });
    ipcMain.handle("planner:replan", (_event, goalId: string, failureTaskId: string) => {
      return this.deps.planner.replan(goalId, failureTaskId);
    });
    ipcMain.handle("planner:complete-task", (_event, goalId: string, taskId: string, output?: any) => {
      this.deps.planner.completeTask(goalId, taskId, output);
    });
    ipcMain.handle("planner:fail-task", (_event, goalId: string, taskId: string) => {
      this.deps.planner.failTask(goalId, taskId);
    });
    ipcMain.handle("planner:execute-ready", async (_event, goalId: string) => {
      return await this.deps.planner.executeReady(goalId);
    });
    ipcMain.handle("planner:get-critical-path", (_event, goalId: string) => {
      return this.deps.planner.getCriticalPath(goalId);
    });

    // --- M16: Agent Runtime ---
    ipcMain.handle("runtime:state", () => {
      return this.deps.agentRuntime.getState();
    });
    ipcMain.handle("runtime:execute", async (_event, agentName: string, task: any, sharedCtx?: any) => {
      return await this.deps.agentRuntime.execute(agentName, task, sharedCtx);
    });
    ipcMain.handle("runtime:execute-parallel", async (_event, agentNames: string[], task: any) => {
      return await this.deps.agentRuntime.executeParallel(agentNames, task);
    });
    ipcMain.handle("runtime:message", (_event, from: string, to: string, message: any) => {
      this.deps.agentRuntime.sendMessage(from, to, message);
    });
    ipcMain.handle("runtime:inbox", (_event, agentName: string) => {
      return this.deps.agentRuntime.getInbox(agentName);
    });
    ipcMain.handle("runtime:context", (_event, agentName: string) => {
      return this.deps.agentRuntime.getSharedContext(agentName);
    });
    ipcMain.handle("runtime:set-context", (_event, agentName: string, key: string, value: any) => {
      this.deps.agentRuntime.setSharedContext(agentName, key, value);
    });
    ipcMain.handle("runtime:artifacts", (_event, agentName: string) => {
      return this.deps.agentRuntime.getArtifacts(agentName);
    });
    ipcMain.handle("runtime:agents", () => {
      return this.deps.agentRuntime.getRegisteredAgents();
    });

    // --- M16: Desktop Automation ---
    ipcMain.handle("automation:mouse-click", async (_event, options: any) => {
      return await this.deps.desktopAutomation.mouseClick(options);
    });
    ipcMain.handle("automation:mouse-move", async (_event, x: number, y: number, duration?: number) => {
      return await this.deps.desktopAutomation.mouseMove(x, y, duration);
    });
    ipcMain.handle("automation:mouse-drag", async (_event, fromX: number, fromY: number, toX: number, toY: number, duration?: number) => {
      return await this.deps.desktopAutomation.mouseDrag(fromX, fromY, toX, toY, duration);
    });
    ipcMain.handle("automation:mouse-scroll", async (_event, deltaX: number, deltaY: number) => {
      return await this.deps.desktopAutomation.mouseScroll(deltaX, deltaY);
    });
    ipcMain.handle("automation:keyboard-type", async (_event, text: string, delay?: number) => {
      return await this.deps.desktopAutomation.keyboardType(text, delay);
    });
    ipcMain.handle("automation:keyboard-hotkey", async (_event, keys: string[]) => {
      return await this.deps.desktopAutomation.keyboardHotkey(keys);
    });
    ipcMain.handle("automation:keyboard-sequence", async (_event, steps: any[]) => {
      return await this.deps.desktopAutomation.keyboardSequence(steps);
    });
    ipcMain.handle("automation:screenshot", async (_event, region?: any) => {
      return await this.deps.desktopAutomation.screenshot(region);
    });
    ipcMain.handle("automation:windows", () => {
      return this.deps.desktopAutomation.getWindowList();
    });
    ipcMain.handle("automation:focus-window", async (_event, windowTitle: string) => {
      return await this.deps.desktopAutomation.focusWindow(windowTitle);
    });
    ipcMain.handle("automation:close-window", async (_event, windowTitle: string) => {
      return await this.deps.desktopAutomation.closeWindow(windowTitle);
    });
    ipcMain.handle("automation:clipboard-read", () => {
      return this.deps.desktopAutomation.clipboardRead();
    });
    ipcMain.handle("automation:clipboard-write", (_event, text: string) => {
      this.deps.desktopAutomation.clipboardWrite(text);
    });
    ipcMain.handle("automation:ocr", async (_event, imagePath: string) => {
      return await this.deps.desktopAutomation.ocrExtract(imagePath);
    });
    ipcMain.handle("automation:accessibility-tree", async () => {
      return await this.deps.desktopAutomation.getAccessibilityTree();
    });

    // --- M16: Workflow Engine ---
    ipcMain.handle("workflow:state", () => {
      return this.deps.workflowEngine.getState();
    });
    ipcMain.handle("workflow:create", (_event, workflow: any) => {
      return this.deps.workflowEngine.createWorkflow(workflow);
    });
    ipcMain.handle("workflow:get", (_event, workflowId: string) => {
      return this.deps.workflowEngine.getWorkflow(workflowId);
    });
    ipcMain.handle("workflow:delete", (_event, workflowId: string) => {
      this.deps.workflowEngine.deleteWorkflow(workflowId);
    });
    ipcMain.handle("workflow:enable", (_event, workflowId: string) => {
      this.deps.workflowEngine.enableWorkflow(workflowId);
    });
    ipcMain.handle("workflow:disable", (_event, workflowId: string) => {
      this.deps.workflowEngine.disableWorkflow(workflowId);
    });
    ipcMain.handle("workflow:execute", async (_event, workflowId: string, data?: any) => {
      return await this.deps.workflowEngine.executeWorkflow(workflowId, data);
    });
    ipcMain.handle("workflow:tick", async () => {
      await this.deps.workflowEngine.tick();
    });
    ipcMain.handle("workflow:active", () => {
      return this.deps.workflowEngine.getActiveExecutions();
    });
    ipcMain.handle("workflow:history", (_event, workflowId?: string) => {
      return this.deps.workflowEngine.getHistory(workflowId);
    });

    // --- M16: Observability ---
    ipcMain.handle("obs:state", () => {
      return this.deps.observability.getState();
    });
    ipcMain.handle("obs:execution-graph", () => {
      return this.deps.observability.getExecutionGraph();
    });
    ipcMain.handle("obs:goal-timeline", (_event, goalId: string) => {
      return this.deps.observability.getGoalTimeline(goalId);
    });
    ipcMain.handle("obs:cost-summary", () => {
      return this.deps.observability.getCostSummary();
    });
    ipcMain.handle("obs:record-execution", (_event, event: any) => {
      this.deps.observability.recordExecution(event);
    });
    ipcMain.handle("obs:performance-metrics", () => {
      return this.deps.observability.getPerformanceMetrics();
    });
    ipcMain.handle("obs:live-stream", () => {
      return this.deps.observability.getLiveStream();
    });

    // --- M16: Persistence ---
    ipcMain.handle("persistence:state", () => {
      return this.deps.persistence.getState();
    });
    ipcMain.handle("persistence:create-checkpoint", (_event, checkpoint: any) => {
      return this.deps.persistence.createCheckpoint(checkpoint);
    });
    ipcMain.handle("persistence:get-checkpoint", (_event, id: string) => {
      return this.deps.persistence.getCheckpoint(id);
    });
    ipcMain.handle("persistence:restore-checkpoint", (_event, id: string) => {
      return this.deps.persistence.restoreCheckpoint(id);
    });
    ipcMain.handle("persistence:list-checkpoints", (_event, goalId?: string) => {
      return this.deps.persistence.listCheckpoints(goalId);
    });
    ipcMain.handle("persistence:enqueue", (_event, queue: string, item: any) => {
      return this.deps.persistence.enqueue(queue, item);
    });
    ipcMain.handle("persistence:dequeue", (_event, queue: string) => {
      return this.deps.persistence.dequeue(queue);
    });
    ipcMain.handle("persistence:peek-queue", (_event, queue: string) => {
      return this.deps.persistence.peekQueue(queue);
    });
    ipcMain.handle("persistence:record-history", (_event, entry: any) => {
      return this.deps.persistence.recordHistory(entry);
    });
    ipcMain.handle("persistence:history", (_event, filters?: any) => {
      return this.deps.persistence.getHistory(filters);
    });
    ipcMain.handle("persistence:export", () => {
      return this.deps.persistence.exportAll();
    });
    ipcMain.handle("persistence:import", (_event, data: any) => {
      return this.deps.persistence.importAll(data);
    });
    ipcMain.handle("persistence:state-versions", (_event, key: string) => {
      return this.deps.persistence.listVersions(key);
    });
    ipcMain.handle("persistence:restore-version", (_event, key: string, version: number) => {
      return this.deps.persistence.restoreVersion(key, version);
    });
    ipcMain.handle("persistence:cleanup", (_event, maxHistory?: number) => {
      this.deps.persistence.cleanup(maxHistory);
    });

    // --- M17: Workforce Manager ---
    ipcMain.handle("workforce:state", () => {
      return this.deps.workforceManager.getState();
    });
    ipcMain.handle("workforce:workers", () => {
      return this.deps.workforceManager.getAllWorkers();
    });
    ipcMain.handle("workforce:get-worker", (_event, workerId: string) => {
      return this.deps.workforceManager.getWorker(workerId);
    });
    ipcMain.handle("workforce:set-status", (_event, workerId: string, status: string) => {
      return this.deps.workforceManager.setWorkerStatus(workerId, status as any);
    });
    ipcMain.handle("workforce:route", (_event, capability: string) => {
      return this.deps.workforceManager.routeToWorker(capability);
    });
    ipcMain.handle("workforce:assign-task", (_event, workerId: string, taskId: string) => {
      return this.deps.workforceManager.assignTask(workerId, taskId);
    });
    ipcMain.handle("workforce:complete-task", (_event, workerId: string, taskId: string, output?: unknown) => {
      return this.deps.workforceManager.completeTask(workerId, taskId, output);
    });
    ipcMain.handle("workforce:fail-task", (_event, workerId: string, taskId: string, error: string) => {
      return this.deps.workforceManager.failTask(workerId, taskId, error);
    });
    ipcMain.handle("workforce:assignments", () => {
      return this.deps.workforceManager.getAssignments();
    });
    ipcMain.handle("workforce:register", (_event, config: any) => {
      return this.deps.workforceManager.registerWorker(
        config.name, config.role, config.cli, config.capabilities, config.options
      );
    });
    ipcMain.handle("workforce:unregister", (_event, workerId: string) => {
      return this.deps.workforceManager.unregisterWorker(workerId);
    });
    ipcMain.handle("workforce:reset-all", () => {
      this.deps.workforceManager.resetAll();
    });

    // --- M17: CLI Controller ---
    ipcMain.handle("cli:state", () => {
      return this.deps.cliController.getState();
    });
    ipcMain.handle("cli:adapters", () => {
      return this.deps.cliController.getAdapters();
    });
    ipcMain.handle("cli:spawn", (_event, workerId: string, cliName: string, prompt: string, cwd?: string) => {
      return this.deps.cliController.spawn(workerId, cliName, prompt, cwd);
    });
    ipcMain.handle("cli:stop", (_event, workerId: string) => {
      return this.deps.cliController.stop(workerId);
    });
    ipcMain.handle("cli:send-input", (_event, workerId: string, input: string) => {
      return this.deps.cliController.sendInput(workerId, input);
    });
    ipcMain.handle("cli:output", (_event, workerId: string) => {
      return this.deps.cliController.getOutput(workerId);
    });
    ipcMain.handle("cli:tail-output", (_event, workerId: string, lines?: number) => {
      return this.deps.cliController.getTailOutput(workerId, lines);
    });
    ipcMain.handle("cli:active", () => {
      return this.deps.cliController.getActiveProcesses();
    });
    ipcMain.handle("cli:stop-all", () => {
      this.deps.cliController.stopAll();
    });

    // --- M17: Review Pipeline ---
    ipcMain.handle("review:state", () => {
      return this.deps.reviewPipeline.getState();
    });
    ipcMain.handle("review:active", () => {
      return this.deps.reviewPipeline.getActiveReviews();
    });
    ipcMain.handle("review:get", (_event, reviewId: string) => {
      return this.deps.reviewPipeline.getReview(reviewId);
    });
    ipcMain.handle("review:create", (_event, params: any) => {
      return this.deps.reviewPipeline.createReview(
        params.title, params.description, params.authorWorkerId,
        params.outputSummary, params.outputFiles, params.options
      );
    });
    ipcMain.handle("review:assign-reviewer", (_event, reviewId: string, reviewerId: string) => {
      return this.deps.reviewPipeline.assignReviewer(reviewId, reviewerId);
    });
    ipcMain.handle("review:start", (_event, reviewId: string) => {
      return this.deps.reviewPipeline.startReview(reviewId);
    });
    ipcMain.handle("review:add-note", (_event, reviewId: string, author: string, content: string, lineRef?: string) => {
      return this.deps.reviewPipeline.addReviewNote(reviewId, author, content, lineRef);
    });
    ipcMain.handle("review:verdict", (_event, reviewId: string, verdict: string, reason?: string) => {
      return this.deps.reviewPipeline.submitVerdict(reviewId, verdict as any, reason);
    });
    ipcMain.handle("review:fixes-applied", (_event, reviewId: string, summary: string, files: string[]) => {
      return this.deps.reviewPipeline.fixesApplied(reviewId, summary, files);
    });
    ipcMain.handle("review:complete-verification", (_event, reviewId: string, approved: boolean) => {
      return this.deps.reviewPipeline.completeVerification(reviewId, approved);
    });
    ipcMain.handle("review:cancel", (_event, reviewId: string) => {
      return this.deps.reviewPipeline.cancelReview(reviewId);
    });

    console.log("[AIOS] IPC handlers registered (M12 + M13 + M14 + M15 + M16 + M17)");
  }
}
