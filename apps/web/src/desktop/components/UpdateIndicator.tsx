/**
 * UpdateIndicator — Shows auto-update status in the UI.
 *
 * Displays a badge when updates are available, downloading, or ready to install.
 * Only visible when running inside Electron.
 */

"use client";

import { isDesktop, onUpdateEvent, checkForUpdates, installUpdate } from "@/lib/electron";
import { useState, useEffect, useCallback } from "react";

interface UpdateState {
  status: "idle" | "checking" | "available" | "downloading" | "downloaded" | "error";
  version?: string;
  progress?: number;
  error?: string;
}

export function UpdateIndicator() {
  const [updateState, setUpdateState] = useState<UpdateState>({ status: "idle" });

  useEffect(() => {
    if (!isDesktop()) return;

    const cleanup = onUpdateEvent((event, data) => {
      switch (event) {
        case "update:checking":
          setUpdateState({ status: "checking" });
          break;
        case "update:available":
          setUpdateState({
            status: "available",
            version: (data as { version: string })?.version,
          });
          break;
        case "update:progress":
          setUpdateState({
            status: "downloading",
            progress: Math.round((data as { percent: number })?.percent ?? 0),
          });
          break;
        case "update:downloaded":
          setUpdateState({
            status: "downloaded",
            version: (data as { version: string })?.version,
          });
          break;
        case "update:error":
          setUpdateState({
            status: "error",
            error: (data as { error: string })?.error,
          });
          break;
        case "update:not-available":
          setUpdateState({ status: "idle" });
          break;
      }
    });

    return cleanup;
  }, []);

  const handleCheckForUpdates = useCallback(() => {
    checkForUpdates();
  }, []);

  const handleInstall = useCallback(() => {
    installUpdate();
  }, []);

  if (!isDesktop()) return null;

  // Don't show anything when idle
  if (updateState.status === "idle") {
    return (
      <button
        onClick={handleCheckForUpdates}
        className="text-xs text-white/30 hover:text-white/60 transition-colors"
        title="Check for updates"
      >
        v0.9.0
      </button>
    );
  }

  // Checking
  if (updateState.status === "checking") {
    return (
      <div className="flex items-center gap-1.5 text-xs text-white/40">
        <div className="w-3 h-3 border border-white/20 border-t-white/60 rounded-full animate-spin" />
        <span>Checking…</span>
      </div>
    );
  }

  // Update available
  if (updateState.status === "available") {
    return (
      <button
        onClick={handleCheckForUpdates}
        className="flex items-center gap-1.5 text-xs text-amber-400/80 hover:text-amber-400 transition-colors"
        title={`Update available: ${updateState.version}`}
      >
        <svg width="12" height="12" viewBox="0 0 12 12" className="fill-current">
          <path d="M6 1l2 4h3l-2.5 3 1 4L6 9 2.5 12l1-4L1 5h3z" />
        </svg>
        <span>Update available</span>
      </button>
    );
  }

  // Downloading
  if (updateState.status === "downloading") {
    return (
      <div className="flex items-center gap-2 text-xs text-white/40" title={`Downloading: ${updateState.progress}%`}>
        <div className="w-16 h-1 bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500/60 rounded-full transition-all duration-300"
            style={{ width: `${updateState.progress ?? 0}%` }}
          />
        </div>
        <span>{updateState.progress ?? 0}%</span>
      </div>
    );
  }

  // Ready to install
  if (updateState.status === "downloaded") {
    return (
      <button
        onClick={handleInstall}
        className="flex items-center gap-1.5 text-xs text-emerald-400/80 hover:text-emerald-400 transition-colors"
        title={`Update ready: ${updateState.version}`}
      >
        <svg width="12" height="12" viewBox="0 0 12 12" className="fill-current">
          <path d="M6 1v7M3 5l3 3 3-3M2 10h8" stroke="currentColor" strokeWidth="1.5" fill="none" />
        </svg>
        <span>Restart to update</span>
      </button>
    );
  }

  // Error
  if (updateState.status === "error") {
    return (
      <button
        onClick={handleCheckForUpdates}
        className="text-xs text-red-400/60 hover:text-red-400 transition-colors"
        title={`Update error: ${updateState.error}`}
      >
        Update failed
      </button>
    );
  }

  return null;
}

export default UpdateIndicator;
