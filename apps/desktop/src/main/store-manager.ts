/**
 * StoreManager — Persistent key-value storage via electron-store.
 */

import Store from "electron-store";

interface StoreSchema {
  "window:bounds": { x: number; y: number; width: number; height: number };
  "window:isMaximized": boolean;
  "settings:theme": "dark" | "light" | "system";
  "settings:apiUrl": string;
  "settings:notifications": boolean;
  "settings:compactMode": boolean;
  "settings:fontSize": number;
  "settings:defaultWorkspace": string;
  "lastSync": string;
  "gateway:connected": boolean;
}

export class StoreManager {
  private store: Store<StoreSchema>;

  constructor() {
    this.store = new Store<StoreSchema>({
      name: "aios-desktop-config",
      defaults: {
        "window:bounds": { x: 0, y: 0, width: 1400, height: 900 },
        "window:isMaximized": false,
        "settings:theme": "dark",
        "settings:apiUrl": "http://localhost:8080",
        "settings:notifications": true,
        "settings:compactMode": false,
        "settings:fontSize": 14,
        "settings:defaultWorkspace": "conversation",
        "lastSync": "",
        "gateway:connected": false,
      },
    });
  }

  get<K extends keyof StoreSchema>(key: K): StoreSchema[K] {
    return this.store.get(key);
  }

  set<K extends keyof StoreSchema>(key: K, value: StoreSchema[K]): void {
    this.store.set(key, value);
  }

  delete<K extends keyof StoreSchema>(key: K): void {
    this.store.delete(key);
  }

  clear(): void {
    this.store.clear();
  }

  getAll(): StoreSchema {
    return this.store.store;
  }

  // Convenience methods
  getWindowBounds() {
    return this.get("window:bounds");
  }

  setWindowBounds(bounds: { x: number; y: number; width: number; height: number }) {
    this.set("window:bounds", bounds);
  }

  getTheme(): "dark" | "light" | "system" {
    return this.get("settings:theme");
  }

  setTheme(theme: "dark" | "light" | "system") {
    this.set("settings:theme", theme);
  }

  getApiUrl(): string {
    return this.get("settings:apiUrl");
  }

  setApiUrl(url: string) {
    this.set("settings:apiUrl", url);
  }

  isGatewayConnected(): boolean {
    return this.get("gateway:connected");
  }

  setGatewayConnected(connected: boolean) {
    this.set("gateway:connected", connected);
  }
}
