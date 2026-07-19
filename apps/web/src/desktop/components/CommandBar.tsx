"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Send, Mic, MicOff, Paperclip, Globe, Brain, ChevronDown,
  Plus, Image, Clipboard, FolderOpen, Target, Loader2,
} from "lucide-react";
import { api, type AgentInfo, type ModelInfo } from "@/lib/api";
import { useVoiceStream, type VoiceState } from "@/hooks/useVoiceStream";

// ---------------------------------------------------------------------------
// Global AI Command Bar — visible across all workspaces
// ---------------------------------------------------------------------------

interface CommandBarProps {
  /** Called when user executes a message. Conversation workspace intercepts this. */
  onExecute: (message: string, opts: { agent: string; model: string }) => void;
  /** Called to submit a goal (autonomous planning + execution). */
  onGoal?: (message: string) => void;
  /** When true, the bar shows a streaming indicator instead of the send button */
  streaming?: boolean;
  /** Called to stop an in-progress stream */
  onStop?: () => void;
}

export function CommandBar({ onExecute, onGoal, streaming = false, onStop }: CommandBarProps) {
  const [message, setMessage] = useState("");
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedAgent, setSelectedAgent] = useState("default");
  const [selectedModel, setSelectedModel] = useState("");
  const [memoryOn, setMemoryOn] = useState(true);
  const [internetOn, setInternetOn] = useState(false);
  const [showAgentMenu, setShowAgentMenu] = useState(false);
  const [showModelMenu, setShowModelMenu] = useState(false);
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Voice stream — server-side STT/TTS via WebSocket
  const voice = useVoiceStream({
    agent: selectedAgent,
    model: selectedModel,
    autoConnect: false,
    onTranscript: useCallback((text: string) => {
      setMessage((prev) => prev + (prev ? " " : "") + text);
    }, []),
  });

  // Fetch agents + models on mount
  useEffect(() => {
    api.agents().then(setAgents).catch(() => {});
    api.models().then(setModels).catch(() => {});
  }, []);

  // Auto-grow textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }, [message]);

  // Close menus on outside click
  useEffect(() => {
    const handler = () => { setShowAgentMenu(false); setShowModelMenu(false); setShowAttachMenu(false); };
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, []);

  const handleSubmit = useCallback(() => {
    const trimmed = message.trim();
    if (!trimmed || streaming) return;
    onExecute(trimmed, { agent: selectedAgent, model: selectedModel });
    setMessage("");
    // reset height
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }, [message, streaming, selectedAgent, selectedModel, onExecute]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
      return;
    }
    // Shift+Enter = newline (default behavior)
  };

  // Voice input — push-to-talk via voice stream
  const toggleVoice = useCallback(async () => {
    if (voice.state === "listening" || voice.state === "transcribing" || voice.state === "planning" || voice.state === "executing") {
      voice.stopListening();
      return;
    }
    if (voice.state === "speaking") {
      voice.interrupt();
      return;
    }
    await voice.startListening();
  }, [voice]);

  const selectedAgentInfo = agents.find((a) => a.name === selectedAgent);

  return (
    <div
      className="shrink-0"
      style={{
        borderTop: "1px solid var(--border)",
        background: "var(--bg-subtle)",
      }}
    >
      {/* Top toolbar row */}
      <div
        className="flex items-center gap-1 px-4 py-1.5 overflow-x-auto"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        {/* Attach button */}
        <div className="relative">
          <ToolbarButton
            icon={<Plus size={14} />}
            label="Attach"
            onClick={(e) => { e.stopPropagation(); setShowAttachMenu(!showAttachMenu); }}
          />
          {showAttachMenu && (
            <div
              className="absolute bottom-full left-0 mb-1 py-1 rounded-lg z-50 min-w-[160px]"
              style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-strong)", boxShadow: "var(--shadow-md)" }}
              onClick={(e) => e.stopPropagation()}
            >
              <AttachMenuItem icon={<Paperclip size={13} />} label="File" shortcut="⌘U" />
              <AttachMenuItem icon={<FolderOpen size={13} />} label="Folder" />
              <AttachMenuItem icon={<Image size={13} />} label="Image" />
              <AttachMenuItem icon={<Clipboard size={13} />} label="Clipboard" shortcut="⌘⇧V" />
            </div>
          )}
        </div>

        <div className="w-px h-4 mx-1" style={{ background: "var(--border)" }} />

        {/* Agent selector */}
        <div className="relative">
          <ToolbarButton
            icon={<span className="w-2 h-2 rounded-full" style={{ background: "var(--accent)" }} />}
            label={selectedAgent}
            suffix={<ChevronDown size={10} />}
            onClick={(e) => { e.stopPropagation(); setShowAgentMenu(!showAgentMenu); }}
          />
          {showAgentMenu && (
            <div
              className="absolute bottom-full left-0 mb-1 py-1 rounded-lg z-50 min-w-[180px]"
              style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-strong)", boxShadow: "var(--shadow-md)" }}
              onClick={(e) => e.stopPropagation()}
            >
              {agents.length === 0 && (
                <div className="px-3 py-2 text-xs" style={{ color: "var(--text-muted)" }}>Loading agents…</div>
              )}
              {agents.map((a) => (
                <button
                  key={a.name}
                  className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-left transition-colors"
                  style={{
                    color: a.name === selectedAgent ? "var(--accent)" : "var(--text-secondary)",
                    background: a.name === selectedAgent ? "var(--surface-active)" : "transparent",
                    border: "none",
                    cursor: "pointer",
                  }}
                  onClick={() => { setSelectedAgent(a.name); setShowAgentMenu(false); }}
                >
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--accent)" }} />
                  <span className="font-medium">{a.name}</span>
                  <span className="ml-auto truncate max-w-[80px]" style={{ color: "var(--text-muted)" }}>
                    {a.model}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Model selector */}
        <div className="relative">
          <ToolbarButton
            icon={<span style={{ fontSize: "0.6rem", fontWeight: 700 }}>AI</span>}
            label={selectedModel || "auto"}
            suffix={<ChevronDown size={10} />}
            onClick={(e) => { e.stopPropagation(); setShowModelMenu(!showModelMenu); }}
          />
          {showModelMenu && (
            <div
              className="absolute bottom-full left-0 mb-1 py-1 rounded-lg z-50 min-w-[200px]"
              style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-strong)", boxShadow: "var(--shadow-md)" }}
              onClick={(e) => e.stopPropagation()}
            >
              <button
                className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-left"
                style={{
                  color: !selectedModel ? "var(--accent)" : "var(--text-secondary)",
                  background: !selectedModel ? "var(--surface-active)" : "transparent",
                  border: "none",
                  cursor: "pointer",
                }}
                onClick={() => { setSelectedModel(""); setShowModelMenu(false); }}
              >
                Auto (let AIOS decide)
              </button>
              {models.map((m) => (
                <button
                  key={m.id}
                  className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-left"
                  style={{
                    color: m.id === selectedModel ? "var(--accent)" : "var(--text-secondary)",
                    background: m.id === selectedModel ? "var(--surface-active)" : "transparent",
                    border: "none",
                    cursor: "pointer",
                  }}
                  onClick={() => { setSelectedModel(m.id); setShowModelMenu(false); }}
                >
                  <span className="font-medium">{m.id}</span>
                  <span className="ml-auto" style={{ color: "var(--text-muted)" }}>{m.provider}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex-1" />

        {/* Toggle buttons */}
        <ToggleChip
          icon={<Brain size={12} />}
          label="Memory"
          active={memoryOn}
          onClick={() => setMemoryOn(!memoryOn)}
        />
        <ToggleChip
          icon={<Globe size={12} />}
          label="Internet"
          active={internetOn}
          onClick={() => setInternetOn(!internetOn)}
        />
        <ToggleChip
          icon={<Mic size={12} />}
          label="Always-on"
          active={voice.alwaysOn}
          onClick={voice.toggleAlwaysOn}
        />
      </div>

      {/* Input row */}
      <div className="flex items-end gap-2 px-4 py-3">
        {/* Voice button */}
        <button
          className="btn-icon shrink-0"
          style={{
            width: 36,
            height: 36,
            borderRadius: "50%",
            border: voice.state !== "idle" ? "1.5px solid var(--danger)" : "1px solid var(--border)",
            background: voice.state === "listening" ? "rgba(59,130,246,0.1)"
              : voice.state === "transcribing" || voice.state === "planning" || voice.state === "executing" ? "rgba(234,179,8,0.1)"
              : voice.state === "speaking" ? "rgba(34,197,94,0.1)"
              : voice.state !== "idle" ? "rgba(239,68,68,0.1)" : "transparent",
            color: voice.state === "listening" ? "#3b82f6"
              : voice.state === "transcribing" || voice.state === "planning" || voice.state === "executing" ? "#eab308"
              : voice.state === "speaking" ? "#22c55e"
              : voice.state !== "idle" ? "var(--danger)" : "var(--text-secondary)",
            transition: "all 0.15s",
          }}
          onClick={toggleVoice}
          title={
            voice.state === "listening" ? "Stop listening"
            : voice.state === "transcribing" ? "Transcribing..."
            : voice.state === "planning" || voice.state === "executing" ? "Processing..."
            : voice.state === "speaking" ? "Interrupt"
            : voice.alwaysOn ? "Voice input (Always-on)" : "Voice input (Push to talk)"
          }
        >
          {(voice.state === "transcribing" || voice.state === "planning" || voice.state === "executing") ? <Loader2 size={16} className="animate-spin" />
            : voice.state !== "idle" ? <MicOff size={16} />
            : <Mic size={16} />}
        </button>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Tell AIOS what you'd like to do…"
          rows={1}
          className="flex-1 bg-transparent outline-none resize-none text-sm leading-relaxed"
          style={{
            color: "var(--text-primary)",
            maxHeight: "160px",
            fontFamily: "var(--font-sans)",
          }}
        />

        {/* Execute / Stop button */}
        {streaming ? (
          <button
            className="btn-icon shrink-0"
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              border: "1.5px solid var(--danger)",
              background: "rgba(239,68,68,0.1)",
              color: "var(--danger)",
            }}
            onClick={onStop}
            title="Stop generation"
          >
            <span className="block w-3 h-3 rounded-sm" style={{ background: "var(--danger)" }} />
          </button>
        ) : (
          <>
            {onGoal && (
              <button
                className="btn-icon shrink-0"
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "50%",
                  border: "1px solid var(--border)",
                  background: "transparent",
                  color: message.trim() ? "var(--accent)" : "var(--text-muted)",
                  transition: "all 0.15s",
                }}
                onClick={() => {
                  const trimmed = message.trim();
                  if (!trimmed) return;
                  onGoal(trimmed);
                  setMessage("");
                  if (textareaRef.current) textareaRef.current.style.height = "auto";
                }}
                disabled={!message.trim()}
                title="Create goal (autonomous planning + execution)"
              >
                <Target size={16} />
              </button>
            )}
            <button
              className="btn-icon shrink-0"
              style={{
                width: 36,
                height: 36,
                borderRadius: "50%",
                border: "none",
                background: message.trim() ? "var(--accent)" : "var(--surface)",
                color: message.trim() ? "#fff" : "var(--text-muted)",
                transition: "all 0.15s",
              }}
              onClick={handleSubmit}
              disabled={!message.trim()}
              title="Execute (⌘Enter)"
            >
              <Send size={16} />
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ToolbarButton({
  icon,
  label,
  suffix,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  suffix?: React.ReactNode;
  onClick: (e: React.MouseEvent) => void;
}) {
  return (
    <button
      className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs transition-colors"
      style={{
        color: "var(--text-secondary)",
        background: "transparent",
        border: "none",
        cursor: "pointer",
        whiteSpace: "nowrap",
      }}
      onClick={onClick}
    >
      {icon}
      <span>{label}</span>
      {suffix}
    </button>
  );
}

function ToggleChip({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs transition-colors"
      style={{
        color: active ? "var(--accent)" : "var(--text-muted)",
        background: active ? "var(--accent-glow)" : "transparent",
        border: `1px solid ${active ? "var(--accent)" : "var(--border)"}`,
        cursor: "pointer",
        whiteSpace: "nowrap",
      }}
      onClick={onClick}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

function AttachMenuItem({
  icon,
  label,
  shortcut,
}: {
  icon: React.ReactNode;
  label: string;
  shortcut?: string;
}) {
  return (
    <button
      className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-left transition-colors"
      style={{ color: "var(--text-secondary)", background: "transparent", border: "none", cursor: "pointer" }}
    >
      {icon}
      <span className="flex-1">{label}</span>
      {shortcut && (
        <kbd className="text-[0.55rem] px-1 py-0.5 rounded" style={{ background: "var(--surface)", color: "var(--text-muted)" }}>
          {shortcut}
        </kbd>
      )}
    </button>
  );
}
