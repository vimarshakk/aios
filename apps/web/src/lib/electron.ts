"use client";

/**
 * Detect whether the app is running inside the Electron desktop shell.
 */
export function isDesktop(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof (window as unknown as { electronAPI?: unknown }).electronAPI !== "undefined"
  );
}

function invoke(method: string, ...args: unknown[]): void {
  const api = getElectronAPI() as
    | { invoke?: (m: string, ...a: unknown[]) => void }
    | null;
  api?.invoke?.(method, ...args);
}

export function minimizeWindow(): void {
  invoke("minimize");
}

export function maximizeWindow(): void {
  invoke("maximize");
}

export function closeWindow(): void {
  invoke("close");
}

export function getElectronAPI(): unknown | null {
  if (typeof window === "undefined") return null;
  return (window as unknown as { electronAPI?: unknown }).electronAPI ?? null;
}

export default isDesktop;

declare global {
  interface Window {
    electronAPI?: unknown;
    aios?: {
      app: {
        platform(): Promise<string>;
      };
      window: {
        isVisible(): Promise<boolean>;
        minimize(): void;
        maximize(): void;
        close(): void;
      };
      [key: string]: unknown;
    };
  }
}

type UpdateListener = (event: string, data?: { version?: string }) => void;

export function onUpdateEvent(listener: UpdateListener): () => void {
  const api = getElectronAPI() as { onUpdate?: (cb: UpdateListener) => void } | null;
  api?.onUpdate?.(listener);
  return () => {};
}

export function checkForUpdates(): void {
  invoke("check-for-updates");
}

export function installUpdate(): void {
  invoke("install-update");
}
