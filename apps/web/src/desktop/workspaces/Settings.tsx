"use client";

import { useThemeStore, useSessionStore } from "../state";
import { useState, useEffect } from "react";
import { cn } from "@/lib/cn";
import { api, type ModelInfo } from "@/lib/api";
import {
  Settings, Monitor, Sun, Moon, Palette,
  Bot, Globe, Keyboard, Info, ChevronRight,
  Loader2,
} from "lucide-react";

interface SettingsSection {
  id: string;
  label: string;
  icon: React.ComponentType<{ size?: number }>;
}

const sections: SettingsSection[] = [
  { id: "general", label: "General", icon: Settings },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "models", label: "Models", icon: Bot },
  { id: "network", label: "Network", icon: Globe },
  { id: "keyboard", label: "Keyboard", icon: Keyboard },
  { id: "about", label: "About", icon: Info },
];

export function SettingsWorkspace() {
  const [activeSection, setActiveSection] = useState("general");

  return (
    <div className="flex h-full">
      {/* Settings nav */}
      <div
        className="w-52 shrink-0 overflow-y-auto py-3"
        style={{ borderRight: "1px solid var(--border)" }}
      >
        {sections.map((section) => {
          const Icon = section.icon;
          const isActive = activeSection === section.id;
          return (
            <button
              key={section.id}
              className={cn("settings-nav-item", isActive && "active")}
              onClick={() => setActiveSection(section.id)}
            >
              <Icon size={15} />
              {section.label}
              <ChevronRight size={12} className="ml-auto opacity-40" />
            </button>
          );
        })}
      </div>

      {/* Settings content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeSection === "general" && <GeneralSettings />}
        {activeSection === "appearance" && <AppearanceSettings />}
        {activeSection === "models" && <ModelSettings />}
        {activeSection === "network" && <NetworkSettings />}
        {activeSection === "keyboard" && <KeyboardSettings />}
        {activeSection === "about" && <AboutSettings />}
      </div>
    </div>
  );
}

// --- General ---
function GeneralSettings() {
  const { assistantName, setAssistantName, currentProject, setProject } = useSessionStore();

  return (
    <div className="max-w-lg space-y-6">
      <SettingsGroup title="Assistant">
        <SettingsRow label="Name">
          <input
            value={assistantName}
            onChange={(e) => setAssistantName(e.target.value)}
            className="settings-input"
            placeholder="AIOS"
          />
        </SettingsRow>
        <SettingsRow label="Project">
          <input
            value={currentProject ?? ""}
            onChange={(e) => setProject(e.target.value || null)}
            className="settings-input"
            placeholder="No project"
          />
        </SettingsRow>
      </SettingsGroup>

      <SettingsGroup title="Startup">
        <SettingsRow label="Default workspace">
          <select className="settings-select">
            <option>Conversation</option>
            <option>Projects</option>
            <option>Goals</option>
          </select>
        </SettingsRow>
        <SettingsRow label="Open last session">
          <Toggle defaultChecked />
        </SettingsRow>
      </SettingsGroup>
    </div>
  );
}

// --- Appearance ---
function AppearanceSettings() {
  const { mode, setMode, accent, setAccent } = useThemeStore();

  const modes: { value: typeof mode; icon: React.ComponentType<{ size?: number }>; label: string }[] = [
    { value: "dark", icon: Moon, label: "Dark" },
    { value: "light", icon: Sun, label: "Light" },
    { value: "system", icon: Monitor, label: "System" },
  ];

  const accents = [
    { value: "orange" as const, color: "#FF6B35" },
    { value: "graphite" as const, color: "#6B7280" },
    { value: "emerald" as const, color: "#10B981" },
    { value: "violet" as const, color: "#8B5CF6" },
  ];

  return (
    <div className="max-w-lg space-y-6">
      <SettingsGroup title="Theme">
        <SettingsRow label="Mode">
          <div className="flex gap-2">
            {modes.map((m) => {
              const Icon = m.icon;
              const isActive = mode === m.value;
              return (
                <button
                  key={m.value}
                  className={cn("settings-theme-btn", isActive && "active")}
                  onClick={() => setMode(m.value)}
                >
                  <Icon size={16} />
                  {m.label}
                </button>
              );
            })}
          </div>
        </SettingsRow>
        <SettingsRow label="Accent">
          <div className="flex gap-3">
            {accents.map((a) => (
              <button
                key={a.value}
                className={cn(
                  "w-8 h-8 rounded-full transition-all",
                  accent === a.value ? "ring-2 ring-offset-2" : "opacity-60 hover:opacity-100",
                )}
                style={{
                  background: a.color,
                  ringColor: accent === a.value ? a.color : undefined,
                  "--tw-ring-color": a.color,
                } as React.CSSProperties}
                onClick={() => setAccent(a.value)}
              />
            ))}
          </div>
        </SettingsRow>
      </SettingsGroup>
    </div>
  );
}

// --- Models ---
function ModelSettings() {
  const [ollamaUrl, setOllamaUrl] = useState("http://localhost:11434");
  const [selectedModel, setSelectedModel] = useState("qwen3:latest");
  const [models, setModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.models().then((data: ModelInfo[]) => {
      const names = data.map((m) => m.id ?? m.name).filter((n): n is string => Boolean(n));
      setModels(names);
      if (names.length > 0 && !names.includes(selectedModel)) {
        setSelectedModel(names[0]);
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-lg space-y-6">
      <SettingsGroup title="Ollama">
        <SettingsRow label="Endpoint">
          <input
            value={ollamaUrl}
            onChange={(e) => setOllamaUrl(e.target.value)}
            className="settings-input"
            placeholder="http://localhost:11434"
          />
        </SettingsRow>
        <SettingsRow label="Model">
          {loading ? (
            <span className="flex items-center gap-2 text-sm" style={{ color: "var(--text-muted)" }}>
              <Loader2 size={14} className="animate-spin" /> Loading…
            </span>
          ) : (
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="settings-select"
            >
              {models.length > 0 ? models.map((m) => (
                <option key={m} value={m}>{m}</option>
              )) : (
                <>
                  <option>qwen3:latest</option>
                  <option>qwen2.5-coder:7b</option>
                  <option>nomic-embed-text:latest</option>
                </>
              )}
            </select>
          )}
        </SettingsRow>
      </SettingsGroup>

      <SettingsGroup title="Parameters">
        <SettingsRow label="Temperature">
          <input
            type="range"
            min={0}
            max={1}
            step={0.1}
            defaultValue={0.7}
            className="w-full accent-orange-500"
          />
        </SettingsRow>
        <SettingsRow label="Context window">
          <select className="settings-select">
            <option>2048</option>
            <option>4096</option>
            <option>8192</option>
          </select>
        </SettingsRow>
      </SettingsGroup>
    </div>
  );
}

// --- Network ---
function NetworkSettings() {
  const [gatewayUrl, setGatewayUrl] = useState("http://localhost:8080");
  const [connected, setConnected] = useState<boolean | null>(null);

  useEffect(() => {
    api.health().then(() => setConnected(true)).catch(() => setConnected(false));
  }, []);

  return (
    <div className="max-w-lg space-y-6">
      <SettingsGroup title="Gateway">
        <SettingsRow label="Endpoint">
          <input
            value={gatewayUrl}
            onChange={(e) => setGatewayUrl(e.target.value)}
            className="settings-input"
            placeholder="http://localhost:8080"
          />
        </SettingsRow>
        <SettingsRow label="Status">
          {connected === null ? (
            <span className="flex items-center gap-2 text-sm" style={{ color: "var(--text-muted)" }}>
              <Loader2 size={14} className="animate-spin" /> Checking…
            </span>
          ) : connected ? (
            <span className="flex items-center gap-2 text-sm" style={{ color: "var(--green)" }}>
              <span className="w-2 h-2 rounded-full bg-current" />
              Connected
            </span>
          ) : (
            <span className="flex items-center gap-2 text-sm" style={{ color: "var(--red)" }}>
              <span className="w-2 h-2 rounded-full bg-current" />
              Disconnected
            </span>
          )}
        </SettingsRow>
      </SettingsGroup>

      <SettingsGroup title="Features">
        <SettingsRow label="Memory">
          <Toggle defaultChecked />
        </SettingsRow>
        <SettingsRow label="Internet">
          <Toggle />
        </SettingsRow>
      </SettingsGroup>
    </div>
  );
}

// --- Keyboard ---
function KeyboardSettings() {
  const shortcuts = [
    ["⌘K", "Open command palette"],
    ["⌘1-8", "Switch workspace"],
    ["⌘,", "Open settings"],
    ["⌘\\", "Toggle sidebar"],
    ["⌘]", "Toggle right panel"],
    ["⌘Enter", "Execute prompt"],
    ["⌘L", "Focus prompt (in Conversation)"],
    ["Esc", "Close modals / Cancel"],
  ];

  return (
    <div className="max-w-lg space-y-4">
      <p className="text-xs mb-4" style={{ color: "var(--text-secondary)" }}>
        Global keyboard shortcuts. Some are workspace-specific.
      </p>
      <div className="space-y-1">
        {shortcuts.map(([key, desc]) => (
          <div key={key} className="settings-shortcut-row">
            <kbd className="settings-kbd">{key}</kbd>
            <span className="text-sm" style={{ color: "var(--text-secondary)" }}>{desc}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- About ---
function AboutSettings() {
  return (
    <div className="max-w-lg space-y-4">
      <SettingsGroup title="AIOS">
        <SettingsRow label="Version">
          <span className="text-sm" style={{ color: "var(--text-secondary)" }}>v0.7.0</span>
        </SettingsRow>
        <SettingsRow label="Runtime">
          <span className="text-sm" style={{ color: "var(--text-secondary)" }}>Ollama (local)</span>
        </SettingsRow>
        <SettingsRow label="License">
          <span className="text-sm" style={{ color: "var(--text-secondary)" }}>Apache 2.0</span>
        </SettingsRow>
      </SettingsGroup>
    </div>
  );
}

// --- Shared components ---
function SettingsGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3
        className="text-xs font-semibold uppercase tracking-wider mb-3"
        style={{ color: "var(--text-muted)" }}
      >
        {title}
      </h3>
      <div
        className="rounded-xl p-4 space-y-3"
        style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
      >
        {children}
      </div>
    </div>
  );
}

function SettingsRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-sm shrink-0" style={{ color: "var(--text-primary)" }}>{label}</span>
      <div className="flex-1 flex justify-end">{children}</div>
    </div>
  );
}

function Toggle({ defaultChecked = false }: { defaultChecked?: boolean }) {
  const [on, setOn] = useState(defaultChecked);
  return (
    <button
      className="settings-toggle"
      style={{
        background: on ? "var(--accent)" : "var(--surface-alt)",
        borderColor: on ? "var(--accent)" : "var(--border)",
      }}
      onClick={() => setOn(!on)}
    >
      <span
        className="settings-toggle-knob"
        style={{ transform: on ? "translateX(16px)" : "translateX(2px)" }}
      />
    </button>
  );
}
