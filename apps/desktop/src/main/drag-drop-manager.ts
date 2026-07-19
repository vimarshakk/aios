/**
 * DragDropManager — Native drag-and-drop support.
 *
 * Handles file drops from OS into the app window.
 * Sends dropped files to the renderer via IPC.
 */

import { BrowserWindow } from "electron";

export interface DroppedFile {
  path: string;
  name: string;
  size: number;
  type: string;
}

export type DropHandler = (files: DroppedFile[]) => void;

export class DragDropManager {
  private window: BrowserWindow | null = null;
  private handler: DropHandler | null = null;

  /**
   * Enable drag-and-drop on a window.
   */
  enable(window: BrowserWindow): void {
    this.window = window;

    // Prevent default drag behavior in web content
    window.webContents.on("will-navigate", (e) => {
      e.preventDefault();
    });
  }

  /**
   * Set the drop handler.
   */
  onDrop(handler: DropHandler): void {
    this.handler = handler;
  }

  /**
   * Handle files dropped (called from webContents).
   */
  handleDrop(files: DroppedFile[]): void {
    this.handler?.(files);
  }

  /**
   * Check if file is a supported type.
   */
  static isSupported(filePath: string): boolean {
    const ext = filePath.split(".").pop()?.toLowerCase() ?? "";
    const supported = [
      "json", "txt", "md", "csv",
      "aios", "aios-memory",
      "png", "jpg", "jpeg", "gif", "webp",
      "pdf",
    ];
    return supported.includes(ext);
  }

  /**
   * Parse dropped files from web content.
   */
  static parseDroppedFiles(filePaths: string[]): DroppedFile[] {
    const fs = require("fs");
    const path = require("path");

    return filePaths
      .filter((p) => this.isSupported(p))
      .map((filePath) => {
        try {
          const stats = fs.statSync(filePath);
          return {
            path: filePath,
            name: path.basename(filePath),
            size: stats.size,
            type: path.extname(filePath).slice(1),
          };
        } catch {
          return null;
        }
      })
      .filter((f): f is DroppedFile => f !== null);
  }

  /**
   * Cleanup.
   */
  destroy(): void {
    this.window = null;
    this.handler = null;
  }
}

export default DragDropManager;
