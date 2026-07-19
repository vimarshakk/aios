/**
 * ClipboardManager — Native clipboard operations.
 *
 * Supports:
 * - Text copy/paste
 * - Image copy/paste (native image)
 * - HTML copy/paste
 * - Rich content (files, memory entries)
 */

import { clipboard, nativeImage } from "electron";

export interface ClipboardContent {
  type: "text" | "image" | "html" | "files" | "empty";
  text?: string;
  html?: string;
  image?: string; // base64 data URL
  files?: string[];
}

export class ClipboardManager {
  /**
   * Read clipboard content.
   */
  read(): ClipboardContent {
    // Check for image first
    const image = clipboard.readImage();
    if (!image.isEmpty()) {
      return {
        type: "image",
        image: image.toDataURL(),
      };
    }

    // Check for HTML
    const html = clipboard.readHTML();
    if (html) {
      return {
        type: "html",
        html,
      };
    }

    // Check for files
    const files = clipboard.read("public.file-url");
    if (files) {
      const filePaths = files.split("\n").filter((f) => f.startsWith("file://"));
      if (filePaths.length > 0) {
        return {
          type: "files",
          files: filePaths.map((f) => decodeURIComponent(f.replace("file://", ""))),
        };
      }
    }

    // Fall back to text
    const text = clipboard.readText();
    if (text) {
      return {
        type: "text",
        text,
      };
    }

    return { type: "empty" };
  }

  /**
   * Write text to clipboard.
   */
  writeText(text: string): void {
    clipboard.writeText(text);
  }

  /**
   * Write HTML to clipboard.
   */
  writeHTML(html: string): void {
    clipboard.writeHTML(html);
  }

  /**
   * Write image to clipboard.
   */
  writeImage(dataUrl: string): void {
    const image = nativeImage.createFromDataURL(dataUrl);
    clipboard.writeImage(image);
  }

  /**
   * Write rich content to clipboard.
   */
  write(content: ClipboardContent): void {
    switch (content.type) {
      case "text":
        if (content.text) this.writeText(content.text);
        break;
      case "html":
        if (content.html) this.writeHTML(content.html);
        break;
      case "image":
        if (content.image) this.writeImage(content.image);
        break;
      case "files":
        if (content.files?.length) {
          // Write file paths as text (Electron limitation)
          clipboard.writeText(content.files.join("\n"));
        }
        break;
    }
  }

  /**
   * Copy memory entry to clipboard as formatted text.
   */
  copyMemoryEntry(entry: {
    type: string;
    content: string;
    timestamp?: string;
    source?: string;
  }): void {
    const parts = [
      `[${entry.type}]`,
      entry.content,
      entry.timestamp ? `at ${entry.timestamp}` : "",
      entry.source ? `from ${entry.source}` : "",
    ].filter(Boolean);

    this.writeText(parts.join("\n"));
  }

  /**
   * Copy memory entry as HTML.
   */
  copyMemoryEntryHTML(entry: {
    type: string;
    content: string;
    timestamp?: string;
    source?: string;
  }): void {
    const html = `
      <div style="font-family: -apple-system, sans-serif; padding: 8px; border: 1px solid #333; border-radius: 4px;">
        <div style="color: #888; font-size: 12px; margin-bottom: 4px;">
          ${entry.type}${entry.timestamp ? ` · ${entry.timestamp}` : ""}
        </div>
        <div style="color: #fff;">${entry.content}</div>
        ${entry.source ? `<div style="color: #666; font-size: 11px; margin-top: 4px;">Source: ${entry.source}</div>` : ""}
      </div>
    `;

    this.writeHTML(html);
    this.writeText(`[${entry.type}] ${entry.content}`);
  }

  /**
   * Check if clipboard has text.
   */
  hasText(): boolean {
    return clipboard.readText().length > 0;
  }

  /**
   * Clear clipboard.
   */
  clear(): void {
    clipboard.clear();
  }
}

export default ClipboardManager;
