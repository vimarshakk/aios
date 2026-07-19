/**
 * TypeScript declarations for the Electron desktop API.
 *
 * Exposes `window.aios` to the renderer process via preload script.
 */

import type { AiosDesktopAPI } from "../preload/index";

declare global {
  interface Window {
    aios: AiosDesktopAPI;
  }
}

export {};
