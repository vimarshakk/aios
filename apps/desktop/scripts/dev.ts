/**
 * Dev script — Starts Next.js dev server + Electron in development mode.
 *
 * Usage: tsx scripts/dev.ts
 *
 * Flow:
 * 1. Start Next.js dev server on port 3000
 * 2. Wait for it to be ready
 * 3. Compile TypeScript (main + preload)
 * 4. Launch Electron with devtools
 */

import { spawn, ChildProcess } from "child_process";
import { existsSync, mkdirSync } from "fs";
import path from "path";

const ROOT = path.resolve(__dirname, "..");
const WEB_APP = path.resolve(ROOT, "../web");

let nextProcess: ChildProcess | null = null;
let electronProcess: ChildProcess | null = null;

// ---------------------------------------------------------------------------
// Cleanup
// ---------------------------------------------------------------------------

function cleanup() {
  console.log("\n[Dev] Shutting down...");
  if (electronProcess) {
    electronProcess.kill("SIGTERM");
    electronProcess = null;
  }
  if (nextProcess) {
    nextProcess.kill("SIGTERM");
    nextProcess = null;
  }
  process.exit(0);
}

process.on("SIGINT", cleanup);
process.on("SIGTERM", cleanup);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function log(prefix: string, msg: string) {
  console.log(`[${prefix}] ${msg}`);
}

async function waitForPort(port: number, timeout = 30000): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try {
      const res = await fetch(`http://localhost:${port}`);
      if (res.ok) return;
    } catch {
      // not ready yet
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Port ${port} not ready after ${timeout}ms`);
}

// ---------------------------------------------------------------------------
// Step 1: Start Next.js dev server
// ---------------------------------------------------------------------------

function startNextDev(): Promise<void> {
  return new Promise((resolve, reject) => {
    log("Next", "Starting Next.js dev server...");

    nextProcess = spawn("pnpm", ["dev"], {
      cwd: WEB_APP,
      stdio: "pipe",
      env: {
        ...process.env,
        PORT: "3000",
        NODE_ENV: "development",
      },
    });

    nextProcess.stdout?.on("data", (data: Buffer) => {
      const msg = data.toString().trim();
      if (msg) log("Next", msg);
    });

    nextProcess.stderr?.on("data", (data: Buffer) => {
      const msg = data.toString().trim();
      if (msg && !msg.includes("WARNING")) log("Next", msg);
    });

    nextProcess.on("error", (err) => {
      log("Next", `Error: ${err.message}`);
      reject(err);
    });

    nextProcess.on("exit", (code) => {
      if (code !== 0 && code !== null) {
        log("Next", `Exited with code ${code}`);
      }
    });

    // Wait for server to be ready
    waitForPort(3000)
      .then(() => {
        log("Next", "Ready on http://localhost:3000");
        resolve();
      })
      .catch(reject);
  });
}

// ---------------------------------------------------------------------------
// Step 2: Compile TypeScript
// ---------------------------------------------------------------------------

async function compileTypeScript(): Promise<void> {
  log("TSC", "Compiling main process TypeScript...");

  // Ensure output directories exist
  const mainOut = path.join(ROOT, "dist/main");
  const preloadOut = path.join(ROOT, "dist/preload");
  if (!existsSync(mainOut)) mkdirSync(mainOut, { recursive: true });
  if (!existsSync(preloadOut)) mkdirSync(preloadOut, { recursive: true });

  // Compile main
  await new Promise<void>((resolve, reject) => {
    const proc = spawn("npx", ["tsc", "-p", "tsconfig.main.json"], {
      cwd: ROOT,
      stdio: "pipe",
    });

    proc.stdout?.on("data", (data: Buffer) => log("TSC", data.toString().trim()));
    proc.stderr?.on("data", (data: Buffer) => log("TSC", data.toString().trim()));

    proc.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`TypeScript main compilation failed with code ${code}`));
    });
  });

  log("TSC", "Compiling preload TypeScript...");

  // Compile preload
  await new Promise<void>((resolve, reject) => {
    const proc = spawn("npx", ["tsc", "-p", "tsconfig.preload.json"], {
      cwd: ROOT,
      stdio: "pipe",
    });

    proc.stdout?.on("data", (data: Buffer) => log("TSC", data.toString().trim()));
    proc.stderr?.on("data", (data: Buffer) => log("TSC", data.toString().trim()));

    proc.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`TypeScript preload compilation failed with code ${code}`));
    });
  });

  log("TSC", "TypeScript compiled successfully");
}

// ---------------------------------------------------------------------------
// Step 3: Launch Electron
// ---------------------------------------------------------------------------

function launchElectron(): Promise<void> {
  return new Promise((resolve) => {
    log("Electron", "Launching Electron...");

    electronProcess = spawn(
      "npx",
      ["electron", ".", "--enable-logging"],
      {
        cwd: ROOT,
        stdio: "pipe",
        env: {
          ...process.env,
          NODE_ENV: "development",
          ELECTRON_ENABLE_LOGGING: "1",
          ELECTRON_ENABLE_STACK_DUMPING: "1",
        },
      },
    );

    electronProcess.stdout?.on("data", (data: Buffer) => {
      const msg = data.toString().trim();
      if (msg) log("Electron", msg);
    });

    electronProcess.stderr?.on("data", (data: Buffer) => {
      const msg = data.toString().trim();
      if (msg) log("Electron", msg);
    });

    electronProcess.on("exit", (code) => {
      log("Electron", `Exited with code ${code}`);
      cleanup();
    });

    electronProcess.on("error", (err) => {
      log("Electron", `Error: ${err.message}`);
      cleanup();
    });

    // Electron is running, resolve immediately
    resolve();
  });
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  console.log("╔══════════════════════════════════════╗");
  console.log("║        AIOS Desktop — Dev Mode       ║");
  console.log("╚══════════════════════════════════════╝");
  console.log();

  try {
    // 1. Start Next.js
    await startNextDev();

    // 2. Compile TypeScript
    await compileTypeScript();

    // 3. Launch Electron
    await launchElectron();
  } catch (err) {
    console.error("[Dev] Fatal error:", err);
    cleanup();
  }
}

main();
