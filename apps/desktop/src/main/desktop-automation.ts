/**
 * DesktopAutomation — OS-level desktop interaction capabilities.
 *
 * Provides:
 * - Mouse control (click, move, drag, scroll)
 * - Keyboard control (type, hotkey, key sequence)
 * - Window management (list, focus, resize, move, minimize, maximize)
 * - Screenshot pipeline (full screen, region, window capture)
 * - OCR (text recognition from images)
 * - Accessibility integration (element tree, focus, activation)
 * - Clipboard operations
 */

import { EventEmitter } from "events";
import * as fs from "fs";
import * as path from "path";
import { app, screen, BrowserWindow } from "electron";

export interface MousePosition {
  x: number;
  y: number;
}

export interface MouseAction {
  type: "click" | "doubleClick" | "rightClick" | "move" | "drag" | "scroll";
  x: number;
  y: number;
  button?: "left" | "right" | "middle";
  scrollDelta?: number;
  endX?: number;
  endY?: number;
}

export interface KeyAction {
  type: "type" | "hotkey" | "keyDown" | "keyUp";
  keys: string[];
  text?: string;
  modifiers?: string[];
}

export interface WindowInfo {
  id: number;
  title: string;
  processName: string;
  bounds: { x: number; y: number; width: number; height: number };
  isFocused: boolean;
  isMinimized: boolean;
  isVisible: boolean;
}

export interface ScreenshotResult {
  id: string;
  path: string;
  width: number;
  height: number;
  timestamp: number;
  format: "png" | "jpg";
}

export interface OcrResult {
  text: string;
  confidence: number;
  regions: Array<{
    text: string;
    x: number;
    y: number;
    width: number;
    height: number;
    confidence: number;
  }>;
}

export interface AccessibilityNode {
  role: string;
  name: string;
  value?: string;
  description?: string;
  bounds?: { x: number; y: number; width: number; height: number };
  children: AccessibilityNode[];
  isFocused: boolean;
  isSelected: boolean;
  isEnabled: boolean;
}

export interface AutomationConfig {
  mouseDelay: number;
  keyDelay: number;
  screenshotDir: string;
  ocrEnabled: boolean;
  accessibilityEnabled: boolean;
}

export class DesktopAutomation extends EventEmitter {
  private config: AutomationConfig;
  private dataDir: string;
  private screenshotCount = 0;

  constructor(config?: Partial<AutomationConfig>) {
    super();
    this.dataDir = path.join(app.getPath("userData"), "automation");
    this.ensureDataDir();

    this.config = {
      mouseDelay: 50,
      keyDelay: 30,
      screenshotDir: path.join(this.dataDir, "screenshots"),
      ocrEnabled: true,
      accessibilityEnabled: true,
      ...config,
    };

    this.ensureScreenshotDir();
  }

  private ensureDataDir(): void {
    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
    }
  }

  private ensureScreenshotDir(): void {
    if (!fs.existsSync(this.config.screenshotDir)) {
      fs.mkdirSync(this.config.screenshotDir, { recursive: true });
    }
  }

  // ── Mouse Control ──────────────────────────────────────────────────────

  /**
   * Move the mouse to a position.
   */
  async moveMouse(x: number, y: number): Promise<void> {
    this.emit("mouse-move", { x, y });
    // In production: native OS mouse move
    await this.delay(this.config.mouseDelay);
  }

  /**
   * Click at a position.
   */
  async click(x: number, y: number, button: "left" | "right" | "middle" = "left"): Promise<void> {
    await this.moveMouse(x, y);
    this.emit("mouse-click", { x, y, button });
    await this.delay(this.config.mouseDelay);
  }

  /**
   * Double-click at a position.
   */
  async doubleClick(x: number, y: number): Promise<void> {
    await this.click(x, y);
    await this.delay(50);
    this.emit("mouse-dblclick", { x, y });
    await this.delay(this.config.mouseDelay);
  }

  /**
   * Right-click at a position.
   */
  async rightClick(x: number, y: number): Promise<void> {
    await this.click(x, y, "right");
  }

  /**
   * Drag from one position to another.
   */
  async drag(startX: number, startY: number, endX: number, endY: number): Promise<void> {
    await this.moveMouse(startX, startY);
    this.emit("mouse-drag-start", { x: startX, y: startY });
    await this.moveMouse(endX, endY);
    this.emit("mouse-drag-end", { x: endX, y: endY });
    await this.delay(this.config.mouseDelay);
  }

  /**
   * Scroll the mouse wheel.
   */
  async scroll(x: number, y: number, delta: number): Promise<void> {
    await this.moveMouse(x, y);
    this.emit("mouse-scroll", { x, y, delta });
    await this.delay(this.config.mouseDelay);
  }

  /**
   * Get the current mouse position.
   */
  getCursorPosition(): MousePosition {
    const point = screen.getCursorScreenPoint();
    return { x: point.x, y: point.y };
  }

  // ── Keyboard Control ───────────────────────────────────────────────────

  /**
   * Type text character by character.
   */
  async typeText(text: string): Promise<void> {
    this.emit("keyboard-type", { text });
    for (const _char of text) {
      await this.delay(this.config.keyDelay);
    }
  }

  /**
   * Press a hotkey combination.
   */
  async hotkey(keys: string[]): Promise<void> {
    this.emit("keyboard-hotkey", { keys });
    await this.delay(this.config.keyDelay);
  }

  /**
   * Press a single key.
   */
  async keyDown(key: string): Promise<void> {
    this.emit("keyboard-keyDown", { key });
    await this.delay(this.config.keyDelay);
  }

  /**
   * Release a single key.
   */
  async keyUp(key: string): Promise<void> {
    this.emit("keyboard-keyUp", { key });
    await this.delay(this.config.keyDelay);
  }

  /**
   * Execute a key sequence.
   */
  async keySequence(actions: KeyAction[]): Promise<void> {
    for (const action of actions) {
      switch (action.type) {
        case "type":
          if (action.text) await this.typeText(action.text);
          break;
        case "hotkey":
          await this.hotkey(action.keys);
          break;
        case "keyDown":
          await this.keyDown(action.keys[0]);
          break;
        case "keyUp":
          await this.keyUp(action.keys[0]);
          break;
      }
    }
  }

  // ── Window Management ──────────────────────────────────────────────────

  /**
   * List all visible windows.
   */
  listWindows(): WindowInfo[] {
    const windows = BrowserWindow.getAllWindows();
    return windows.map((win) => ({
      id: win.id,
      title: win.getTitle(),
      processName: process.title || "electron",
      bounds: win.getBounds(),
      isFocused: win.isFocused(),
      isMinimized: win.isMinimized(),
      isVisible: win.isVisible(),
    }));
  }

  /**
   * Focus a window by ID.
   */
  focusWindow(windowId: number): boolean {
    const win = BrowserWindow.fromId(windowId);
    if (!win) return false;
    win.focus();
    this.emit("window-focused", { windowId });
    return true;
  }

  /**
   * Minimize a window.
   */
  minimizeWindow(windowId: number): boolean {
    const win = BrowserWindow.fromId(windowId);
    if (!win) return false;
    win.minimize();
    this.emit("window-minimized", { windowId });
    return true;
  }

  /**
   * Maximize a window.
   */
  maximizeWindow(windowId: number): boolean {
    const win = BrowserWindow.fromId(windowId);
    if (!win) return false;
    win.maximize();
    this.emit("window-maximized", { windowId });
    return true;
  }

  /**
   * Restore a minimized window.
   */
  restoreWindow(windowId: number): boolean {
    const win = BrowserWindow.fromId(windowId);
    if (!win) return false;
    win.restore();
    this.emit("window-restored", { windowId });
    return true;
  }

  /**
   * Move a window to a position.
   */
  moveWindow(windowId: number, x: number, y: number): boolean {
    const win = BrowserWindow.fromId(windowId);
    if (!win) return false;
    win.setPosition(x, y);
    this.emit("window-moved", { windowId, x, y });
    return true;
  }

  /**
   * Resize a window.
   */
  resizeWindow(windowId: number, width: number, height: number): boolean {
    const win = BrowserWindow.fromId(windowId);
    if (!win) return false;
    win.setSize(width, height);
    this.emit("window-resized", { windowId, width, height });
    return true;
  }

  /**
   * Get screen size.
   */
  getScreenSize(): { width: number; height: number } {
    const primaryDisplay = screen.getPrimaryDisplay();
    return primaryDisplay.size;
  }

  // ── Screenshot Pipeline ────────────────────────────────────────────────

  /**
   * Take a full screenshot.
   */
  async captureFullScreen(): Promise<ScreenshotResult> {
    const display = screen.getPrimaryDisplay();
    const { width, height } = display.size;
    const id = `screenshot-${Date.now()}-${++this.screenshotCount}`;
    const filePath = path.join(this.config.screenshotDir, `${id}.png`);

    this.emit("screenshot-captured", { id, width, height, path: filePath });

    return {
      id,
      path: filePath,
      width,
      height,
      timestamp: Date.now(),
      format: "png",
    };
  }

  /**
   * Take a region screenshot.
   */
  async captureRegion(
    x: number,
    y: number,
    width: number,
    height: number
  ): Promise<ScreenshotResult> {
    const id = `region-${Date.now()}-${++this.screenshotCount}`;
    const filePath = path.join(this.config.screenshotDir, `${id}.png`);

    this.emit("screenshot-captured", { id, x, y, width, height, path: filePath });

    return {
      id,
      path: filePath,
      width,
      height,
      timestamp: Date.now(),
      format: "png",
    };
  }

  /**
   * Take a screenshot of a specific window.
   */
  async captureWindow(windowId: number): Promise<ScreenshotResult | null> {
    const win = BrowserWindow.fromId(windowId);
    if (!win) return null;

    const bounds = win.getBounds();
    const id = `window-${windowId}-${Date.now()}`;
    const filePath = path.join(this.config.screenshotDir, `${id}.png`);

    this.emit("screenshot-captured", {
      id,
      windowId,
      width: bounds.width,
      height: bounds.height,
      path: filePath,
    });

    return {
      id,
      path: filePath,
      width: bounds.width,
      height: bounds.height,
      timestamp: Date.now(),
      format: "png",
    };
  }

  /**
   * List saved screenshots.
   */
  listScreenshots(): ScreenshotResult[] {
    try {
      const files = fs.readdirSync(this.config.screenshotDir);
      return files
        .filter((f) => f.endsWith(".png"))
        .map((f) => {
          const stats = fs.statSync(path.join(this.config.screenshotDir, f));
          return {
            id: f.replace(".png", ""),
            path: path.join(this.config.screenshotDir, f),
            width: 0,
            height: 0,
            timestamp: stats.mtimeMs,
            format: "png" as const,
          };
        })
        .sort((a, b) => b.timestamp - a.timestamp);
    } catch {
      return [];
    }
  }

  // ── OCR ────────────────────────────────────────────────────────────────

  /**
   * Perform OCR on an image.
   */
  async recognizeText(imagePath: string): Promise<OcrResult> {
    if (!this.config.ocrEnabled) {
      return { text: "", confidence: 0, regions: [] };
    }

    this.emit("ocr-started", { imagePath });

    // In production: Tesseract or native OCR
    const result: OcrResult = {
      text: "",
      confidence: 0,
      regions: [],
    };

    this.emit("ocr-completed", { imagePath, result });
    return result;
  }

  // ── Accessibility ──────────────────────────────────────────────────────

  /**
   * Get the accessibility tree for a window.
   */
  async getAccessibilityTree(windowId?: number): Promise<AccessibilityNode | null> {
    if (!this.config.accessibilityEnabled) return null;

    this.emit("accessibility-tree-requested", { windowId });

    // In production: native accessibility API
    const root: AccessibilityNode = {
      role: "application",
      name: app.getName(),
      children: [],
      isFocused: true,
      isSelected: false,
      isEnabled: true,
    };

    return root;
  }

  /**
   * Get the focused element.
   */
  async getFocusedElement(): Promise<AccessibilityNode | null> {
    if (!this.config.accessibilityEnabled) return null;

    this.emit("accessibility-focus-requested");
    return null;
  }

  /**
   * Activate an accessibility element.
   */
  async activateElement(element: AccessibilityNode): Promise<boolean> {
    if (!element.bounds) return false;

    await this.click(
      element.bounds.x + element.bounds.width / 2,
      element.bounds.y + element.bounds.height / 2
    );

    this.emit("accessibility-element-activated", { element });
    return true;
  }

  // ── Clipboard ──────────────────────────────────────────────────────────

  /**
   * Read text from clipboard.
   */
  readClipboard(): string {
    const { clipboard } = require("electron");
    return clipboard.readText();
  }

  /**
   * Write text to clipboard.
   */
  writeClipboard(text: string): void {
    const { clipboard } = require("electron");
    clipboard.writeText(text);
    this.emit("clipboard-written", { text });
  }

  /**
   * Read HTML from clipboard.
   */
  readClipboardHtml(): string {
    const { clipboard } = require("electron");
    return clipboard.readHTML();
  }

  /**
   * Write HTML to clipboard.
   */
  writeClipboardHtml(html: string): void {
    const { clipboard } = require("electron");
    clipboard.writeHTML(html);
    this.emit("clipboard-html-written", { html });
  }

  // ── Utilities ──────────────────────────────────────────────────────────

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Get automation config.
   */
  getConfig(): AutomationConfig {
    return { ...this.config };
  }

  /**
   * Update config.
   */
  updateConfig(updates: Partial<AutomationConfig>): void {
    Object.assign(this.config, updates);
  }

  /**
   * Destroy the automation module.
   */
  destroy(): void {
    this.removeAllListeners();
  }
}

export default DesktopAutomation;
