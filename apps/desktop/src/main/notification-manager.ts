/**
 * NotificationManager — Native OS notifications.
 */

import { Notification, BrowserWindow } from "electron";

export interface NotificationOptions {
  title: string;
  body: string;
  subtitle?: string;
  silent?: boolean;
  onClick?: () => void;
}

export class NotificationManager {
  private permissionsGranted = false;

  async requestPermission(): Promise<boolean> {
    if (process.platform === "darwin") {
      // macOS: check notification permission
      this.permissionsGranted = await Notification.isSupported();
    } else {
      this.permissionsGranted = Notification.isSupported();
    }
    return this.permissionsGranted;
  }

  send(options: NotificationOptions, mainWindow?: BrowserWindow | null) {
    if (!this.permissionsGranted && !Notification.isSupported()) {
      console.warn("[AIOS] Notifications not supported");
      return;
    }

    const notification = new Notification({
      title: options.title,
      body: options.body,
      subtitle: options.subtitle,
      silent: options.silent ?? false,
      icon: undefined, // Will use app icon
    });

    notification.on("click", () => {
      if (mainWindow) {
        mainWindow.show();
        mainWindow.focus();
      }
      options.onClick?.();
    });

    notification.show();
  }

  sendGoalUpdate(goalId: string, status: string, summary: string, mainWindow?: BrowserWindow | null) {
    this.send(
      {
        title: `Goal ${status}`,
        body: summary,
        subtitle: `Goal ID: ${goalId}`,
      },
      mainWindow,
    );
  }

  sendAgentResponse(agentName: string, preview: string, mainWindow?: BrowserWindow | null) {
    this.send(
      {
        title: `${agentName} responded`,
        body: preview.slice(0, 200),
      },
      mainWindow,
    );
  }

  sendConsolidationComplete(episodesProcessed: number, mainWindow?: BrowserWindow | null) {
    this.send(
      {
        title: "Memory Consolidation Complete",
        body: `Processed ${episodesProcessed} episodes`,
      },
      mainWindow,
    );
  }
}
