"use client";

import { useState, useRef, useEffect } from "react";
import type { Worker } from "../../types";
import {
  Terminal, Maximize2, Minimize2, X, Send, Copy,
  ChevronDown, RotateCcw,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Mock terminal output per worker
// ---------------------------------------------------------------------------

const MOCK_OUTPUT: Record<string, string[]> = {
  "claude-code": [
    "$ claude",
    "▸ Initializing Claude Code...",
    "▸ Connected to Anthropic API",
    "",
    "📋 Task: Design API architecture for ecommerce platform",
    "",
    "Analyzing requirements...",
    "  → REST API with OpenAPI spec",
    "  → PostgreSQL schema design",
    "  → JWT authentication flow",
    "  → Rate limiting strategy",
    "",
    "📝 Generating architecture document...",
    "  ✓ Created docs/architecture.md",
    "  ✓ Created openapi.yaml",
    "  ✓ Created db/schema.sql",
    "",
    "✅ Architecture design complete.",
    "   3 files generated, ~240 lines",
  ],
  "opencode": [
    "$ opencode",
    "▸ Workspace: /Users/dev/ecommerce",
    "▸ Model: gpt-4o",
    "",
    "📋 Task: Build React components",
    "",
    "Reading architecture docs...",
    "  → architecture.md loaded",
    "  → openapi.yaml parsed",
    "",
    "Generating components...",
    "  ✓ src/components/ProductCard.tsx",
    "  ✓ src/components/CheckoutForm.tsx",
    "  ✓ src/components/CartSidebar.tsx",
    "  ✓ src/hooks/useCart.ts",
    "",
    "✅ Frontend components generated.",
    "   4 files, 312 lines",
  ],
  "gemini-cli": [
    "$ gemini",
    "▸ Connected to Gemini Pro",
    "",
    "🔍 Researching: Payment gateway integration",
    "",
    "Searching documentation...",
    "  → Stripe API docs",
    "  → Razorpay integration guide",
    "  → Indian payment methods",
    "",
    "📋 Summary:",
    "  → Stripe: Best for international",
    "  → Razorpay: Best for India (UPI, wallets)",
    "  → Recommendation: Dual integration",
    "",
    "✅ Research complete.",
  ],
  "codex-cli": [
    "$ codex",
    "▸ Mode: test-generation",
    "",
    "📋 Task: Generate unit tests",
    "",
    "Scanning codebase...",
    "  → 12 source files found",
    "  → 0 existing tests",
    "",
    "Generating tests...",
    "  ✓ tests/product.test.ts (14 assertions)",
    "  ✓ tests/cart.test.ts (22 assertions)",
    "  ✓ tests/checkout.test.ts (18 assertions)",
    "",
    "Running tests...",
    "  ✓ 54/54 passed (1.2s)",
    "",
    "✅ All tests generated and passing.",
  ],
  "vs-code": [
    "$ code /Users/dev/ecommerce",
    "▸ VS Code opened",
    "",
    "📁 Workspace loaded",
    "  → 47 files",
    "  → TypeScript: 23",
    "  → React: 12",
    "  → Tests: 12",
    "",
    "Diagnostic check...",
    "  ✓ No errors",
    "  ✓ No warnings",
    "  ⚠ 2 unused imports (info)",
  ],
  "browser": [
    "$ playwright install chromium",
    "▸ Chromium installed",
    "",
    "🌐 Opening browser...",
    "  → https://docs.stripe.com/api",
    "",
    "📄 Page loaded (1.2s)",
    "  → Title: Stripe API Reference",
    "  → Content: 847KB",
    "",
    "📸 Screenshot saved: docs/stripe-api.png",
    "",
    "✅ Browser session active.",
  ],
  "docker": [
    "$ docker compose up -d",
    "▸ Building services...",
    "",
    "📦 postgres: Building... done (3.2s)",
    "📦 redis: Building... done (1.1s)",
    "📦 api: Building... done (8.4s)",
    "📦 web: Building... done (12.1s)",
    "",
    "✅ All services started:",
    "  → postgres:5432",
    "  → redis:6379",
    "  → api:8080",
    "  → web:3000",
    "",
    "Health check: all services healthy ✓",
  ],
  "git": [
    "$ git status",
    "On branch feature/ecommerce",
    "",
    "Changes to be committed:",
    "  new file:   docs/architecture.md",
    "  new file:   openapi.yaml",
    "  new file:   db/schema.sql",
    "  new file:   src/components/ProductCard.tsx",
    "  new file:   src/components/CheckoutForm.tsx",
    "",
    "$ git commit -m \"feat: ecommerce architecture + components\"",
    "[feature/ecommerce abc1234] feat: ecommerce architecture + components",
    " 5 files changed, 552 insertions(+)",
  ],
};

// ---------------------------------------------------------------------------
// Terminal view for a single worker
// ---------------------------------------------------------------------------

function TerminalView({ worker, isActive }: { worker: Worker; isActive: boolean }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [input, setInput] = useState("");
  const output = MOCK_OUTPUT[worker.id] ?? [`$ ${worker.command}`, "No output available."];

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [output]);

  const workerColor =
    worker.status === "running" ? "var(--green)" :
    worker.status === "busy" ? "#f59e0b" :
    "var(--text-muted)";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "#0a0a0a",
        borderRadius: "var(--radius-md)",
        border: isActive ? "1px solid var(--accent)" : "1px solid var(--border)",
        overflow: "hidden",
      }}
    >
      {/* Terminal header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "6px 10px",
          background: "#111",
          borderBottom: "1px solid #222",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: workerColor,
              boxShadow: worker.status === "running" ? `0 0 6px ${workerColor}` : "none",
            }}
          />
          <span style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-primary)" }}>
            {worker.name}
          </span>
          <span style={{ fontSize: "0.62rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            {worker.command}
          </span>
        </div>
        <div style={{ display: "flex", gap: "4px" }}>
          <button style={headerBtnStyle}><Copy size={10} /></button>
          <button style={headerBtnStyle}><RotateCcw size={10} /></button>
          <button style={headerBtnStyle}><X size={10} /></button>
        </div>
      </div>

      {/* Terminal body */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflow: "auto",
          padding: "8px 12px",
          fontFamily: "var(--font-mono)",
          fontSize: "0.72rem",
          lineHeight: 1.6,
          color: "#d4d4d4",
        }}
      >
        {output.map((line, i) => (
          <div key={i} style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
            {line.startsWith("$") ? (
              <span style={{ color: "#10b981" }}>{line}</span>
            ) : line.startsWith("✓") || line.startsWith("✅") ? (
              <span style={{ color: "#10b981" }}>{line}</span>
            ) : line.startsWith("⚠") ? (
              <span style={{ color: "#f59e0b" }}>{line}</span>
            ) : line.startsWith("▸") ? (
              <span style={{ color: "#6b7280" }}>{line}</span>
            ) : line.startsWith("📋") || line.startsWith("📝") || line.startsWith("🔍") || line.startsWith("📦") || line.startsWith("🌐") || line.startsWith("📄") || line.startsWith("📸") || line.startsWith("📁") ? (
              <span style={{ color: "#8b5cf6" }}>{line}</span>
            ) : (
              <span>{line}</span>
            )}
          </div>
        ))}
        {/* Blinking cursor */}
        <span
          style={{
            display: "inline-block",
            width: 7,
            height: 14,
            background: "#d4d4d4",
            animation: "blink 1s step-end infinite",
            verticalAlign: "text-bottom",
          }}
        />
      </div>

      {/* Input */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "6px 12px",
          borderTop: "1px solid #222",
          background: "#111",
        }}
      >
        <span style={{ color: "#10b981", fontFamily: "var(--font-mono)", fontSize: "0.72rem", marginRight: 6 }}>$</span>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Send command..."
          style={{
            flex: 1,
            background: "none",
            border: "none",
            outline: "none",
            color: "#d4d4d4",
            fontFamily: "var(--font-mono)",
            fontSize: "0.72rem",
          }}
        />
        <button
          style={{
            background: "var(--accent)",
            border: "none",
            borderRadius: "4px",
            padding: "3px 8px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
          }}
        >
          <Send size={10} color="#fff" />
        </button>
      </div>
    </div>
  );
}

const headerBtnStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  padding: "2px 4px",
  cursor: "pointer",
  color: "var(--text-muted)",
  borderRadius: "3px",
  display: "flex",
  alignItems: "center",
};

// ---------------------------------------------------------------------------
// LiveConsole — grid of terminals
// ---------------------------------------------------------------------------

export function LiveConsole({ workers }: { workers: Worker[] }) {
  const [activeWorker, setActiveWorker] = useState<string | null>(workers[0]?.id ?? null);
  const [layout, setLayout] = useState<"grid" | "focus">("grid");

  const activeWorkers = workers.filter((w) => w.status === "running" || w.status === "busy");
  const displayWorkers = layout === "focus" && activeWorker
    ? workers.filter((w) => w.id === activeWorker)
    : activeWorkers.length > 0
      ? activeWorkers
      : workers.slice(0, 4);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Controls */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 16px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
          {workers.map((w) => (
            <button
              key={w.id}
              onClick={() => setActiveWorker(w.id)}
              style={{
                padding: "3px 8px",
                borderRadius: "9999px",
                fontSize: "0.65rem",
                fontWeight: activeWorker === w.id ? 600 : 400,
                background: activeWorker === w.id ? "var(--accent)" : "var(--surface)",
                color: activeWorker === w.id ? "#fff" : "var(--text-secondary)",
                border: `1px solid ${activeWorker === w.id ? "var(--accent)" : "var(--border)"}`,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              <span
                style={{
                  width: 5,
                  height: 5,
                  borderRadius: "50%",
                  background: w.status === "running" ? "var(--green)" : w.status === "busy" ? "#f59e0b" : "var(--text-muted)",
                }}
              />
              {w.name}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: "4px" }}>
          <button
            onClick={() => setLayout("grid")}
            style={{
              padding: "3px 8px",
              borderRadius: "4px",
              fontSize: "0.65rem",
              background: layout === "grid" ? "var(--surface-active)" : "none",
              color: "var(--text-secondary)",
              border: "1px solid var(--border)",
              cursor: "pointer",
            }}
          >
            Grid
          </button>
          <button
            onClick={() => setLayout("focus")}
            style={{
              padding: "3px 8px",
              borderRadius: "4px",
              fontSize: "0.65rem",
              background: layout === "focus" ? "var(--surface-active)" : "none",
              color: "var(--text-secondary)",
              border: "1px solid var(--border)",
              cursor: "pointer",
            }}
          >
            Focus
          </button>
        </div>
      </div>

      {/* Terminal grid */}
      <div
        style={{
          flex: 1,
          display: "grid",
          gridTemplateColumns: layout === "focus" ? "1fr" : `repeat(${Math.min(displayWorkers.length, 2)}, 1fr)`,
          gridTemplateRows: layout === "focus" ? "1fr" : `repeat(${Math.ceil(displayWorkers.length / 2)}, 1fr)`,
          gap: "8px",
          padding: "8px",
          overflow: "auto",
        }}
      >
        {displayWorkers.map((w) => (
          <TerminalView
            key={w.id}
            worker={w}
            isActive={w.id === activeWorker}
          />
        ))}
      </div>
    </div>
  );
}
