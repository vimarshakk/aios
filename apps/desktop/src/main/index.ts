/**
 * AIOS Desktop — Main Process
 *
 * Electron main process responsible for:
 * - Window management (create, minimize, maximize, close)
 * - System tray with context menu
 * - Native notifications
 * - Auto-update via electron-updater
 * - IPC bridge for renderer process
 * - App lifecycle (ready, activate, window-all-closed)
 */

import { app, BrowserWindow, Menu, Tray, nativeImage, ipcMain, nativeTheme, shell } from "electron";
import path from "path";
import { WindowManager } from "./window-manager";
import { TrayManager } from "./tray-manager";
import { NotificationManager } from "./notification-manager";
import { UpdateManager } from "./update-manager";
import { IpcHandler } from "./ipc-handler";
import { StoreManager } from "./store-manager";
import { ShortcutsManager } from "./shortcuts-manager";
import { ClipboardManager } from "./clipboard-manager";
import { AutoLaunchManager } from "./auto-launch-manager";
import { PowerMonitorManager } from "./power-monitor-manager";
import { FileAssociationManager } from "./file-association-manager";
import { WindowStatePersistence } from "./window-state-persistence";
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

// ---------------------------------------------------------------------------
// Globals
// ---------------------------------------------------------------------------

let windowManager: WindowManager;
let trayManager: TrayManager;
let notificationManager: NotificationManager;
let updateManager: UpdateManager;
let ipcHandler: IpcHandler;
let storeManager: StoreManager;
let shortcutsManager: ShortcutsManager;
let clipboardManager: ClipboardManager;
let autoLaunchManager: AutoLaunchManager;
let powerMonitorManager: PowerMonitorManager;
let fileAssociationManager: FileAssociationManager;
let windowStatePersistence: WindowStatePersistence;
let developerConsole: DeveloperConsole;
let pluginManager: PluginManager;
let advancedWindowManager: AdvancedWindowManager;
let systemIntegration: SystemIntegration;
let cloudSync: CloudSync;
let collaborationManager: CollaborationManager;
let analyticsEngine: AnalyticsEngine;
let aiAssistant: AIAssistant;
let supervisor: Supervisor;
let planner: Planner;
let agentRuntime: AgentRuntime;
let desktopAutomation: DesktopAutomation;
let workflowEngine: WorkflowEngine;
let observability: Observability;
let persistence: Persistence;
let workforceManager: WorkforceManager;
let cliController: CLIController;
let reviewPipeline: ReviewPipeline;

const isDev = !app.isPackaged;
const API_BASE = process.env.AIOS_API_URL || "http://localhost:8080";

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------

app.whenReady().then(async () => {
  // Initialize managers
  storeManager = new StoreManager();
  windowManager = new WindowManager({ isDev, API_BASE });
  trayManager = new TrayManager();
  notificationManager = new NotificationManager();
  updateManager = new UpdateManager();
  shortcutsManager = new ShortcutsManager();
  clipboardManager = new ClipboardManager();
  autoLaunchManager = new AutoLaunchManager();
  powerMonitorManager = new PowerMonitorManager();
  fileAssociationManager = new FileAssociationManager();
  windowStatePersistence = new WindowStatePersistence(storeManager);
  developerConsole = new DeveloperConsole();
  pluginManager = new PluginManager();
  advancedWindowManager = new AdvancedWindowManager({ isDev, API_BASE });
  systemIntegration = new SystemIntegration();
  cloudSync = new CloudSync();
  collaborationManager = new CollaborationManager();
  analyticsEngine = new AnalyticsEngine();
  aiAssistant = new AIAssistant();

  // M16: Initialize Autonomous Intelligence modules
  persistence = new Persistence();
  observability = new Observability();
  supervisor = new Supervisor();
  planner = new Planner();
  agentRuntime = new AgentRuntime();
  desktopAutomation = new DesktopAutomation();
  workflowEngine = new WorkflowEngine();

  // M17: Initialize Developer Mode modules
  workforceManager = new WorkforceManager();
  cliController = new CLIController();
  reviewPipeline = new ReviewPipeline();

  ipcHandler = new IpcHandler({
    windowManager,
    storeManager,
    notificationManager,
    updateManager,
    shortcutsManager,
    clipboardManager,
    autoLaunchManager,
    powerMonitorManager,
    fileAssociationManager,
    developerConsole,
    pluginManager,
    advancedWindowManager,
    systemIntegration,
    cloudSync,
    collaborationManager,
    analyticsEngine,
    aiAssistant,
    supervisor,
    planner,
    agentRuntime,
    desktopAutomation,
    workflowEngine,
    observability,
    persistence,
    workforceManager,
    cliController,
    reviewPipeline,
  });

  // Create main window
  windowManager.createMainWindow();
  const mainWindow = windowManager.getMainWindow()!;

  // Set up tray
  trayManager.createTray(mainWindow);

  // Set up IPC
  ipcHandler.register();

  // M13: Window state persistence
  windowStatePersistence.attach(mainWindow);

  // M13: Register shortcuts
  shortcutsManager.setMainWindow(mainWindow);
  shortcutsManager.registerAll();

  // Register shortcut handlers
  shortcutsManager.on("command-palette", (win) => {
    win?.webContents.send("command-palette:toggle");
  });
  shortcutsManager.on("memory-explorer", (win) => {
    win?.webContents.send("navigate", "memory-explorer");
  });
  shortcutsManager.on("new-conversation", (win) => {
    win?.webContents.send("navigate", "conversation");
  });
  shortcutsManager.on("toggle-sidebar", (win) => {
    win?.webContents.send("sidebar:toggle");
  });
  shortcutsManager.on("show-hide", (win) => {
    if (win?.isVisible()) {
      win.hide();
    } else {
      win?.show();
      win?.focus();
    }
  });

  // M13: Power monitor
  powerMonitorManager.setMainWindow(mainWindow);

  // M13: File association handler
  fileAssociationManager.onFileOpen((event) => {
    mainWindow.webContents.send("file:opened", event);
  });

  // M13: Handle protocol/file args (Windows/Linux)
  fileAssociationManager.handleArgv(process.argv);

  // M14: Developer console — start capturing logs
  developerConsole.startCapture();
  developerConsole.registerIpcHandlers(mainWindow);

  // M14: System integration — Dock badge, tray, progress
  systemIntegration.init(mainWindow);

  // M14: Load plugins
  const manifests = pluginManager.scanPlugins();
  for (const manifest of manifests) {
    pluginManager.loadPlugin(manifest.name);
    await pluginManager.activatePlugin(manifest.name);
  }

  // M15: Start cloud sync if enabled
  if (cloudSync.getConfig().enabled) {
    cloudSync.startSync();
  }

  // M15: Start analytics session
  analyticsEngine.startSession("app", "launch");

  // M17: Start workforce health monitoring
  workforceManager.startHealthCheck();

  // Start auto-updater
  if (!isDev) {
    updateManager.checkForUpdates();
  }

  // Set application menu
  buildMenu();

  // Handle deep links
  setupDeepLinks();

  console.log(`[AIOS] Desktop app ready (${isDev ? "dev" : "prod"})`);
  console.log(`[AIOS] API: ${API_BASE}`);
  console.log(`[AIOS] M13 + M14 + M15 + M16 + M17 active`);
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    windowManager.createMainWindow();
  }
});

app.on("before-quit", async () => {
  shortcutsManager.destroy();
  powerMonitorManager.destroy();
  fileAssociationManager.destroy();
  windowStatePersistence.destroy();
  developerConsole.destroy();
  await pluginManager.destroy();
  advancedWindowManager.destroy();
  systemIntegration.destroy();
  cloudSync.destroy();
  collaborationManager.destroy();
  analyticsEngine.destroy();
  aiAssistant.destroy();
  workflowEngine.destroy();
  desktopAutomation.destroy();
  agentRuntime.destroy();
  planner.destroy();
  supervisor.destroy();
  observability.destroy();
  persistence.destroy();
  reviewPipeline.destroy();
  cliController.destroy();
  workforceManager.destroy();
  trayManager.destroy();
  updateManager.cancel();
});

// ---------------------------------------------------------------------------
// Application menu
// ---------------------------------------------------------------------------

function buildMenu() {
  const template: Electron.MenuItemConstructorOptions[] = [
    {
      label: "AIOS",
      submenu: [
        { label: "About AIOS", role: "about" },
        { type: "separator" },
        {
          label: "Preferences",
          accelerator: "CmdOrCtrl+,",
          click: () => windowManager.getMainWindow()?.webContents.send("navigate", "settings"),
        },
        { type: "separator" },
        { label: "Quit", role: "quit" },
      ],
    },
    {
      label: "Edit",
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "selectAll" },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "reload" },
        { role: "forceReload" },
        { role: "toggleDevTools" },
        { type: "separator" },
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" },
      ],
    },
    {
      label: "Window",
      submenu: [
        { role: "minimize" },
        { role: "zoom" },
        { role: "close" },
      ],
    },
    {
      label: "Help",
      submenu: [
        {
          label: "AIOS Documentation",
          click: () => shell.openExternal("https://aios.dev/docs"),
        },
        {
          label: "Report Issue",
          click: () => shell.openExternal("https://github.com/aios/aios/issues"),
        },
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ---------------------------------------------------------------------------
// Deep links (aios:// protocol)
// ---------------------------------------------------------------------------

function setupDeepLinks() {
  // Register custom protocol
  app.setAsDefaultProtocolClient("aios");

  // Handle protocol URL (macOS)
  app.on("open-url", (_event, url) => {
    handleDeepLink(url);
  });

  // Handle protocol URL (Windows/Linux)
  app.on("second-instance", (_event, commandLine) => {
    const url = commandLine.find((arg) => arg.startsWith("aios://"));
    if (url) handleDeepLink(url);
  });

  // Focus window on deep link
  app.on("activate", () => {
    windowManager.getMainWindow()?.show();
  });
}

function handleDeepLink(url: string) {
  const mainWindow = windowManager.getMainWindow();
  if (!mainWindow) return;

  mainWindow.show();
  mainWindow.focus();

  // Parse and route deep link
  try {
    const parsed = new URL(url);
    const path = parsed.pathname;
    mainWindow.webContents.send("deep-link", { path, params: parsed.searchParams });
  } catch {
    console.error(`[AIOS] Invalid deep link: ${url}`);
  }
}
