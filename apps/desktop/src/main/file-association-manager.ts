/**
 * FileAssociationManager — Handle .aios file associations and protocol URLs.
 *
 * Registers the app as a handler for:
 * - aios:// protocol URLs
 * - .aios files (JSON workspace exports)
 * - .aios-memory files (memory dumps)
 */

import { app, protocol } from "electron";
import * as fs from "fs";
import * as path from "path";

export interface FileOpenEvent {
  type: "protocol" | "file";
  path?: string;
  url?: string;
  data?: unknown;
}

export type FileOpenHandler = (event: FileOpenEvent) => void;

export class FileAssociationManager {
  private handler: FileOpenHandler | null = null;
  private pendingFiles: string[] = [];

  constructor() {
    // Register custom protocol
    app.setAsDefaultProtocolClient("aios");
  }

  /**
   * Set the handler for opened files/protocol URLs.
   */
  onFileOpen(handler: FileOpenHandler): void {
    this.handler = handler;

    // Process any pending files (queued before handler was set)
    for (const filePath of this.pendingFiles) {
      this.processFile(filePath);
    }
    this.pendingFiles = [];
  }

  /**
   * Handle protocol URL (macOS).
   */
  handleProtocolUrl(url: string): void {
    if (this.handler) {
      this.handler({
        type: "protocol",
        url,
      });
    }
  }

  /**
   * Handle protocol URL (Windows/Linux — via command line args).
   */
  handleArgv(argv: string[]): void {
    for (const arg of argv) {
      if (arg.startsWith("aios://")) {
        this.handleProtocolUrl(arg);
      } else if (arg.endsWith(".aios") || arg.endsWith(".aios-memory")) {
        this.processFile(arg);
      }
    }
  }

  /**
   * Process a file path.
   */
  private processFile(filePath: string): void {
    if (!this.handler) {
      this.pendingFiles.push(filePath);
      return;
    }

    try {
      const ext = path.extname(filePath).toLowerCase();

      if (ext === ".aios") {
        // JSON workspace file
        const content = fs.readFileSync(filePath, "utf-8");
        const data = JSON.parse(content);
        this.handler({
          type: "file",
          path: filePath,
          data,
        });
      } else if (ext === ".aios-memory") {
        // Memory dump file
        const content = fs.readFileSync(filePath, "utf-8");
        const data = JSON.parse(content);
        this.handler({
          type: "file",
          path: filePath,
          data,
        });
      }
    } catch (err) {
      console.error(`[FileAssociation] Error processing ${filePath}:`, err);
    }
  }

  /**
   * Get supported file types for open dialog.
   */
  getSupportedFileTypes(): Electron.FileFilter[] {
    return [
      {
        name: "AIOS Files",
        extensions: ["aios", "aios-memory"],
      },
      {
        name: "All Files",
        extensions: ["*"],
      },
    ];
  }

  /**
   * Register file type associations (for installer).
   */
  getFileAssociations(): Electron.FileAssociation[] {
    return [
      {
        ext: "aios",
        name: "AIOS Workspace",
        description: "AIOS workspace export file",
        mimeType: "application/json",
        icon: path.join(__dirname, "../../assets/icon.icns"),
      },
      {
        ext: "aios-memory",
        name: "AIOS Memory Dump",
        description: "AIOS memory dump file",
        mimeType: "application/json",
        icon: path.join(__dirname, "../../assets/icon.icns"),
      },
    ];
  }

  /**
   * Cleanup.
   */
  destroy(): void {
    this.handler = null;
    this.pendingFiles = [];
  }
}

export default FileAssociationManager;
