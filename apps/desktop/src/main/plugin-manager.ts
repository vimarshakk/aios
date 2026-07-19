/**
 * PluginManager — Load, manage, and sandbox desktop plugins.
 *
 * Plugins are loaded from the plugins directory (~/.aios/plugins/).
 * Each plugin is a Node.js module with a standard interface:
 *   - name: string
 *   - version: string
 *   - activate(api: PluginAPI): void
 *   - deactivate(): void
 */

import { app, BrowserWindow } from "electron";
import * as fs from "fs";
import * as path from "path";
import { EventEmitter } from "events";

export interface PluginManifest {
  name: string;
  version: string;
  description?: string;
  author?: string;
  main: string; // entry point relative to plugin dir
  permissions?: string[];
  dependencies?: Record<string, string>;
}

export interface PluginInstance {
  manifest: PluginManifest;
  dir: string;
  exports: PluginModule;
  enabled: boolean;
  loaded: boolean;
}

export interface PluginModule {
  activate?: (api: PluginAPI) => void | Promise<void>;
  deactivate?: () => void | Promise<void>;
}

export interface PluginAPI {
  app: {
    getVersion: () => string;
    getName: () => string;
    getPath: (name: string) => string;
  };
  window: {
    getMainWindow: () => BrowserWindow | null;
    send: (channel: string, ...args: unknown[]) => void;
  };
  storage: {
    get: (key: string) => unknown;
    set: (key: string, value: unknown) => void;
    delete: (key: string) => void;
  };
  log: (message: string) => void;
}

export interface PluginState {
  name: string;
  version: string;
  enabled: boolean;
  loaded: boolean;
  error?: string;
}

export class PluginManager extends EventEmitter {
  private pluginsDir: string;
  private plugins: Map<string, PluginInstance> = new Map();

  constructor() {
    super();
    this.pluginsDir = path.join(app.getPath("userData"), "plugins");
    this.ensurePluginsDir();
  }

  /**
   * Ensure the plugins directory exists.
   */
  private ensurePluginsDir(): void {
    if (!fs.existsSync(this.pluginsDir)) {
      fs.mkdirSync(this.pluginsDir, { recursive: true });
    }
  }

  /**
   * Get the plugins directory path.
   */
  getPluginsDir(): string {
    return this.pluginsDir;
  }

  /**
   * Scan for plugins in the plugins directory.
   */
  scanPlugins(): PluginManifest[] {
    const manifests: PluginManifest[] = [];

    try {
      const entries = fs.readdirSync(this.pluginsDir, { withFileTypes: true });

      for (const entry of entries) {
        if (!entry.isDirectory()) continue;

        const pluginDir = path.join(this.pluginsDir, entry.name);
        const manifestPath = path.join(pluginDir, "plugin.json");

        try {
          if (fs.existsSync(manifestPath)) {
            const raw = fs.readFileSync(manifestPath, "utf-8");
            const manifest: PluginManifest = JSON.parse(raw);
            manifests.push(manifest);
          }
        } catch {
          // Skip invalid plugin directories
        }
      }
    } catch {
      // Plugins dir may not exist yet
    }

    return manifests;
  }

  /**
   * Load a plugin by name.
   */
  loadPlugin(name: string): boolean {
    if (this.plugins.has(name)) {
      return this.plugins.get(name)!.loaded;
    }

    const pluginDir = path.join(this.pluginsDir, name);
    const manifestPath = path.join(pluginDir, "plugin.json");

    if (!fs.existsSync(manifestPath)) {
      return false;
    }

    try {
      const raw = fs.readFileSync(manifestPath, "utf-8");
      const manifest: PluginManifest = JSON.parse(raw);

      const entryPath = path.join(pluginDir, manifest.main);
      if (!fs.existsSync(entryPath)) {
        return false;
      }

      // Load the plugin module
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const exports: PluginModule = require(entryPath);

      const instance: PluginInstance = {
        manifest,
        dir: pluginDir,
        exports,
        enabled: true,
        loaded: true,
      };

      this.plugins.set(name, instance);
      this.emit("plugin-loaded", name);

      return true;
    } catch (err) {
      console.error(`[PluginManager] Failed to load plugin ${name}:`, err);
      return false;
    }
  }

  /**
   * Activate a loaded plugin.
   */
  async activatePlugin(name: string): Promise<boolean> {
    const plugin = this.plugins.get(name);
    if (!plugin || !plugin.loaded || !plugin.enabled) {
      return false;
    }

    try {
      if (plugin.exports.activate) {
        await plugin.exports.activate(this.createPluginAPI(plugin));
      }
      this.emit("plugin-activated", name);
      return true;
    } catch (err) {
      console.error(`[PluginManager] Failed to activate plugin ${name}:`, err);
      return false;
    }
  }

  /**
   * Deactivate a plugin.
   */
  async deactivatePlugin(name: string): Promise<boolean> {
    const plugin = this.plugins.get(name);
    if (!plugin || !plugin.loaded) {
      return false;
    }

    try {
      if (plugin.exports.deactivate) {
        await plugin.exports.deactivate();
      }
      plugin.enabled = false;
      this.emit("plugin-deactivated", name);
      return true;
    } catch (err) {
      console.error(`[PluginManager] Failed to deactivate plugin ${name}:`, err);
      return false;
    }
  }

  /**
   * Unload a plugin.
   */
  async unloadPlugin(name: string): Promise<boolean> {
    const plugin = this.plugins.get(name);
    if (!plugin) return false;

    if (plugin.loaded) {
      await this.deactivatePlugin(name);
    }

    this.plugins.delete(name);
    this.emit("plugin-unloaded", name);
    return true;
  }

  /**
   * Get all loaded plugins.
   */
  getPlugins(): PluginState[] {
    const states: PluginState[] = [];
    for (const [name, plugin] of this.plugins) {
      states.push({
        name,
        version: plugin.manifest.version,
        enabled: plugin.enabled,
        loaded: plugin.loaded,
      });
    }
    return states;
  }

  /**
   * Get a specific plugin.
   */
  getPlugin(name: string): PluginInstance | undefined {
    return this.plugins.get(name);
  }

  /**
   * Check if a plugin is loaded.
   */
  isPluginLoaded(name: string): boolean {
    return this.plugins.get(name)?.loaded ?? false;
  }

  /**
   * Enable a plugin.
   */
  enablePlugin(name: string): boolean {
    const plugin = this.plugins.get(name);
    if (!plugin) return false;
    plugin.enabled = true;
    this.emit("plugin-enabled", name);
    return true;
  }

  /**
   * Disable a plugin.
   */
  disablePlugin(name: string): boolean {
    const plugin = this.plugins.get(name);
    if (!plugin) return false;
    plugin.enabled = false;
    this.emit("plugin-disabled", name);
    return true;
  }

  /**
   * Create a sandboxed API for a plugin.
   */
  private createPluginAPI(plugin: PluginInstance): PluginAPI {
    return {
      app: {
        getVersion: () => app.getVersion(),
        getName: () => app.getName(),
        getPath: (name: string) => app.getPath(name as any),
      },
      window: {
        getMainWindow: () => BrowserWindow.getAllWindows()[0] ?? null,
        send: (channel: string, ...args: unknown[]) => {
          BrowserWindow.getAllWindows().forEach((win) => {
            win.webContents.send(channel, ...args);
          });
        },
      },
      storage: {
        get: (key: string) => {
          try {
            const storePath = path.join(plugin.dir, "store.json");
            if (!fs.existsSync(storePath)) return undefined;
            const data = JSON.parse(fs.readFileSync(storePath, "utf-8"));
            return data[key];
          } catch {
            return undefined;
          }
        },
        set: (key: string, value: unknown) => {
          try {
            const storePath = path.join(plugin.dir, "store.json");
            let data: Record<string, unknown> = {};
            if (fs.existsSync(storePath)) {
              data = JSON.parse(fs.readFileSync(storePath, "utf-8"));
            }
            data[key] = value;
            fs.writeFileSync(storePath, JSON.stringify(data, null, 2));
          } catch (err) {
            console.error(`[Plugin] Storage write error:`, err);
          }
        },
        delete: (key: string) => {
          try {
            const storePath = path.join(plugin.dir, "store.json");
            if (!fs.existsSync(storePath)) return;
            const data = JSON.parse(fs.readFileSync(storePath, "utf-8"));
            delete data[key];
            fs.writeFileSync(storePath, JSON.stringify(data, null, 2));
          } catch (err) {
            console.error(`[Plugin] Storage delete error:`, err);
          }
        },
      },
      log: (message: string) => {
        console.log(`[Plugin:${plugin.manifest.name}] ${message}`);
      },
    };
  }

  /**
   * Destroy all plugins.
   */
  async destroy(): Promise<void> {
    const names = Array.from(this.plugins.keys());
    for (const name of names) {
      await this.unloadPlugin(name);
    }
  }
}

export default PluginManager;
