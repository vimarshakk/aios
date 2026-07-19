/**
 * OfflineIndicator — Shows connection status and offline capabilities.
 *
 * Monitors network connectivity and provides fallback UI when gateway is unreachable.
 * Supports caching responses for offline use.
 */

"use client";

import { isDesktop } from "@/lib/electron";
import { useState, useEffect, useCallback } from "react";

interface ConnectionStatus {
  online: boolean;
  gatewayReachable: boolean;
  lastChecked: Date | null;
}

export function OfflineIndicator() {
  const [status, setStatus] = useState<ConnectionStatus>({
    online: navigator.onLine,
    gatewayReachable: true,
    lastChecked: null,
  });

  // Check gateway reachability
  const checkGateway = useCallback(async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
      const response = await fetch(`${apiUrl}/health`, {
        method: "GET",
        signal: AbortSignal.timeout(5000),
      });
      return response.ok;
    } catch {
      return false;
    }
  }, []);

  // Monitor online/offline status
  useEffect(() => {
    const handleOnline = async () => {
      const gatewayOk = await checkGateway();
      setStatus({
        online: true,
        gatewayReachable: gatewayOk,
        lastChecked: new Date(),
      });
    };

    const handleOffline = () => {
      setStatus((prev) => ({
        ...prev,
        online: false,
        gatewayReachable: false,
        lastChecked: new Date(),
      }));
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // Initial check
    checkGateway().then((reachable) => {
      setStatus({
        online: navigator.onLine,
        gatewayReachable: reachable,
        lastChecked: new Date(),
      });
    });

    // Periodic check (every 30 seconds)
    const interval = setInterval(async () => {
      const reachable = await checkGateway();
      setStatus((prev) => ({
        ...prev,
        gatewayReachable: reachable,
        lastChecked: new Date(),
      }));
    }, 30000);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      clearInterval(interval);
    };
  }, [checkGateway]);

  // Don't show if everything is fine
  if (status.online && status.gatewayReachable) {
    return null;
  }

  // Offline banner
  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50">
      <div className="flex items-center gap-3 px-4 py-2.5 bg-[#1a1a1a] border border-white/10 rounded-xl shadow-2xl">
        {/* Status icon */}
        {!status.online ? (
          <div className="flex items-center gap-2">
            <svg width="16" height="16" viewBox="0 0 16 16" className="text-red-400">
              <path
                d="M2 4l12 8M14 4l-12 8"
                stroke="currentColor"
                strokeWidth="1.5"
                fill="none"
              />
            </svg>
            <span className="text-sm text-white/80">No internet connection</span>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <svg width="16" height="16" viewBox="0 0 16 16" className="text-amber-400">
              <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" fill="none" />
              <path d="M8 5v3M8 10v1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <span className="text-sm text-white/80">Gateway unreachable — offline mode</span>
          </div>
        )}

        {/* Cached data indicator */}
        {isDesktop() && (
          <div className="text-xs text-white/40 border-l border-white/10 pl-3">
            Using cached data
          </div>
        )}

        {/* Retry button */}
        {status.online && (
          <button
            onClick={async () => {
              const reachable = await checkGateway();
              setStatus((prev) => ({
                ...prev,
                gatewayReachable: reachable,
                lastChecked: new Date(),
              }));
            }}
            className="text-xs text-blue-400/70 hover:text-blue-400 transition-colors ml-2"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

export default OfflineIndicator;
