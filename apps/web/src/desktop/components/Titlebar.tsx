/**
 * Titlebar — Custom window title bar for Electron desktop.
 *
 * Replaces the native title bar with a draggable area and window controls.
 * Only rendered when running inside Electron.
 */

"use client";

import { isDesktop, minimizeWindow, maximizeWindow, closeWindow } from "@/lib/electron";
import { useState, useEffect } from "react";

export function Titlebar() {
  const [isMaximized, setIsMaximized] = useState(false);
  const [platform, setPlatform] = useState<string>("");

  useEffect(() => {
    if (isDesktop()) {
      window.aios.app.platform().then(setPlatform);
      window.aios.window.isVisible().then(() => {
        // Track maximize state
      });
    }
  }, []);

  if (!isDesktop()) return null;

  const isMac = platform === "darwin";

  return (
    <div className="h-10 bg-[#0a0a0a] border-b border-white/5 flex items-center select-none drag-region">
      {/* macOS traffic lights spacer */}
      {isMac && <div className="w-20" />}

      {/* App title */}
      <div className="flex-1 text-center text-xs text-white/40 font-medium">
        AIOS
      </div>

      {/* Window controls (Windows/Linux) */}
      {!isMac && (
        <div className="flex items-center no-drag-region">
          <button
            onClick={minimizeWindow}
            className="w-11 h-10 flex items-center justify-center text-white/40 hover:text-white/80 hover:bg-white/5 transition-colors"
            title="Minimize"
          >
            <svg width="12" height="12" viewBox="0 0 12 12">
              <path d="M2 6h8" stroke="currentColor" strokeWidth="1" />
            </svg>
          </button>
          <button
            onClick={maximizeWindow}
            className="w-11 h-10 flex items-center justify-center text-white/40 hover:text-white/80 hover:bg-white/5 transition-colors"
            title={isMaximized ? "Restore" : "Maximize"}
          >
            <svg width="12" height="12" viewBox="0 0 12 12">
              {isMaximized ? (
                <path d="M3 2h6v6H3V2zM5 4h4v4H5V4z" stroke="currentColor" strokeWidth="1" fill="none" />
              ) : (
                <path d="M2 3h8v7H2V3zM3 4h6v6H3V4z" stroke="currentColor" strokeWidth="1" fill="none" />
              )}
            </svg>
          </button>
          <button
            onClick={closeWindow}
            className="w-11 h-10 flex items-center justify-center text-white/40 hover:text-white hover:bg-red-500/80 transition-colors"
            title="Close"
          >
            <svg width="12" height="12" viewBox="0 0 12 12">
              <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}

export default Titlebar;
