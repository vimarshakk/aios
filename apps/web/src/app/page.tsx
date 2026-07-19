"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot, Send, Mic, MicOff, Settings2, Plus,
  Zap, Globe, Code2, Brain, Eye, ChevronDown,
  Volume2, VolumeX, Loader2, Sparkles, Terminal,
  Layers
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { api, type AgentInfo, type ModelInfo } from "@/lib/api";
import { useVoice } from "@/hooks/useVoice";

// -------------------------------------------------------------------------
// Types
// -------------------------------------------------------------------------

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: string;
  model?: string;
  timestamp: Date;
  streaming?: boolean;
}

const AGENT_ICONS: Record<string, React.ReactNode> = {
  default:  <Sparkles size={14} />,
  research: <Globe size={14} />,
  coding:   <Code2 size={14} />,
  browser:  <Globe size={14} />,
  memory:   <Brain size={14} />,
  vision:   <Eye size={14} />,
};

const AGENT_COLORS: Record<string, string> = {
  default:  "#6e7cff",
  research: "#06b6d4",
  coding:   "#10b981",
  browser:  "#f59e0b",
  memory:   "#a78bfa",
  vision:   "#ec4899",
};

// -------------------------------------------------------------------------
// Sidebar
// -------------------------------------------------------------------------

function Sidebar({
  agents,
  models,
  selectedAgent,
  selectedModel,
  onSelectAgent,
  onSelectModel,
  onNewChat,
}: {
  agents: AgentInfo[];
  models: ModelInfo[];
  selectedAgent: string;
  selectedModel: string;
  onSelectAgent: (a: string) => void;
  onSelectModel: (m: string) => void;
  onNewChat: () => void;
}) {
  const [modelOpen, setModelOpen] = useState(false);
  const currentModel = models.find((m) => m.id === selectedModel);

  return (
    <div className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div style={{
          width: 32, height: 32, borderRadius: "50%",
          background: "linear-gradient(135deg, #6e7cff, #a78bfa)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Zap size={16} color="white" />
        </div>
        <div>
          <div style={{ fontWeight: 800, fontSize: "1rem", letterSpacing: "-0.02em" }}>
            <span className="text-gradient">AIOS</span>
          </div>
          <div style={{ fontSize: "0.65rem", color: "var(--aios-text-3)", marginTop: -2 }}>
            AI Operating System
          </div>
        </div>
      </div>

      {/* New Chat */}
      <div style={{ padding: "12px 12px 4px" }}>
        <button onClick={onNewChat} className="btn-ghost" style={{ width: "100%", justifyContent: "center" }}>
          <Plus size={14} /> New Chat
        </button>
      </div>

      {/* Model Picker */}
      <div style={{ padding: "8px 12px" }}>
        <div
          onClick={() => setModelOpen(!modelOpen)}
          style={{
            padding: "8px 12px",
            background: "var(--aios-surface)",
            border: "1px solid var(--aios-border)",
            borderRadius: "var(--r-md)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ fontSize: "0.78rem", color: "var(--aios-text-2)" }}>
            <div style={{ fontSize: "0.65rem", color: "var(--aios-text-3)", marginBottom: 2 }}>MODEL</div>
            <div style={{ color: "var(--aios-text)", fontWeight: 600, fontSize: "0.82rem" }}>
              {currentModel?.id.split("/").pop() || selectedModel.split("/").pop()}
            </div>
          </div>
          <ChevronDown size={14} color="var(--aios-text-3)" style={{ transform: modelOpen ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
        </div>
        <AnimatePresence>
          {modelOpen && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              style={{
                marginTop: 6,
                background: "var(--aios-bg-2)",
                border: "1px solid var(--aios-border)",
                borderRadius: "var(--r-md)",
                overflow: "hidden",
                maxHeight: 250,
                overflowY: "auto",
              }}
            >
              {["ollama", "openai", "anthropic", "gemini", "openrouter"].map((provider) => {
                const providerModels = models.filter((m) => m.provider === provider);
                if (!providerModels.length) return null;
                return (
                  <div key={provider}>
                    <div style={{ padding: "6px 12px 2px", fontSize: "0.6rem", color: "var(--aios-text-3)", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 700 }}>
                      {provider}
                    </div>
                    {providerModels.map((m) => (
                      <div
                        key={m.id}
                        onClick={() => { onSelectModel(m.id); setModelOpen(false); }}
                        style={{
                          padding: "7px 12px",
                          fontSize: "0.8rem",
                          cursor: "pointer",
                          background: selectedModel === m.id ? "rgba(110,124,255,0.1)" : "transparent",
                          color: selectedModel === m.id ? "var(--aios-accent)" : "var(--aios-text-2)",
                          transition: "background 0.15s",
                        }}
                        onMouseEnter={(e) => { if (selectedModel !== m.id) (e.currentTarget as HTMLElement).style.background = "var(--aios-surface)"; }}
                        onMouseLeave={(e) => { if (selectedModel !== m.id) (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                      >
                        {m.id.split("/").pop()}
                        <div style={{ fontSize: "0.65rem", color: "var(--aios-text-3)" }}>{m.description}</div>
                      </div>
                    ))}
                  </div>
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Agents */}
      <div style={{ flex: 1, overflowY: "auto", paddingBottom: 16 }}>
        <div className="sidebar-section">Agents</div>
        {agents.map((agent) => (
          <div
            key={agent.name}
            className={`sidebar-item ${selectedAgent === agent.name ? "active" : ""}`}
            onClick={() => onSelectAgent(agent.name)}
          >
            <span style={{ color: AGENT_COLORS[agent.name] || "var(--aios-accent)" }}>
              {AGENT_ICONS[agent.name] || <Bot size={14} />}
            </span>
            <div style={{ flex: 1, overflow: "hidden" }}>
              <div style={{ fontWeight: 600, fontSize: "0.875rem", textTransform: "capitalize" }}>{agent.name}</div>
              <div style={{ fontSize: "0.65rem", color: "var(--aios-text-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {agent.description}
              </div>
            </div>
          </div>
        ))}

        <div className="sidebar-section" style={{ marginTop: 8 }}>Workspace</div>
        <a href="/agents" className="sidebar-item"><Layers size={14} /> Agent Dashboard</a>
        <a href="/memory" className="sidebar-item"><Brain size={14} /> Memory Browser</a>
        <a href="/tools" className="sidebar-item"><Terminal size={14} /> Tools</a>
      </div>

      {/* Status */}
      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--aios-border)", fontSize: "0.75rem", color: "var(--aios-text-3)", display: "flex", alignItems: "center", gap: 8 }}>
        <span className="status-dot online" />
        Gateway connected
      </div>
    </div>
  );
}

// -------------------------------------------------------------------------
// Message bubble
// -------------------------------------------------------------------------

function MessageBubble({ msg }: { msg: Message }) {
  if (msg.role === "user") {
    return (
      <motion.div
        className="message-user animate-slide-up"
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="bubble">{msg.content}</div>
      </motion.div>
    );
  }

  const agentColor = AGENT_COLORS[msg.agent || "default"] || "var(--aios-accent)";

  return (
    <motion.div
      className="message-assistant"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="avatar" style={{ background: `${agentColor}20`, borderColor: `${agentColor}40`, color: agentColor }}>
        {AGENT_ICONS[msg.agent || "default"] || <Bot size={14} />}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
          <span style={{ fontSize: "0.75rem", fontWeight: 700, color: agentColor, textTransform: "capitalize" }}>
            {msg.agent || "AIOS"}
          </span>
          {msg.model && (
            <span style={{ fontSize: "0.65rem", color: "var(--aios-text-3)", background: "var(--aios-surface)", padding: "1px 8px", borderRadius: "999px", border: "1px solid var(--aios-border)" }}>
              {msg.model.split("/").pop()}
            </span>
          )}
          <span style={{ fontSize: "0.65rem", color: "var(--aios-text-3)" }}>
            {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
        <div className="bubble prose">
          {msg.streaming && !msg.content ? (
            <div style={{ display: "flex", gap: 5, alignItems: "center", padding: "4px 0" }}>
              <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
            </div>
          ) : (
            <ReactMarkdown
              components={{
                code({ node, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || "");
                  const inline = !match;
                  return !inline ? (
                    <SyntaxHighlighter
                      style={oneDark as Record<string, React.CSSProperties>}
                      language={match?.[1] || "text"}
                      PreTag="div"
                      customStyle={{ margin: "8px 0", borderRadius: "var(--r-md)", fontSize: "0.82em" }}
                    >
                      {String(children).replace(/\n$/, "")}
                    </SyntaxHighlighter>
                  ) : (
                    <code className={className} {...props}>{children}</code>
                  );
                },
              }}
            >
              {msg.content || ""}
            </ReactMarkdown>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// -------------------------------------------------------------------------
// Main page
// -------------------------------------------------------------------------

export default function HomePage() {
  const [chats, setChats] = useState<Record<string, Message[]>>({});
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedAgent, setSelectedAgent] = useState("default");
  const [selectedModel, setSelectedModel] = useState("ollama/llama3.2");

  const [sessionIds] = useState<Record<string, string>>({});
  const getSessionId = useCallback((agent: string) => {
    if (!sessionIds[agent]) {
      sessionIds[agent] = `sess_${agent}_${Math.random().toString(36).slice(2, 10)}`;
    }
    return sessionIds[agent];
  }, [sessionIds]);

  const messages = chats[selectedAgent] || [];
  const sessionId = getSessionId(selectedAgent);

  const setMessages = useCallback((updateFn: Message[] | ((prev: Message[]) => Message[])) => {
    setChats((prev) => {
      const current = prev[selectedAgent] || [];
      const updated = typeof updateFn === "function" ? updateFn(current) : updateFn;
      return { ...prev, [selectedAgent]: updated };
    });
  }, [selectedAgent]);

  const [voiceOverlay, setVoiceOverlay] = useState(false);
  const [speakResponses, setSpeakResponses] = useState(false);
  const [mode, setMode] = useState<"single" | "multi">("single");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const stopStreamRef = useRef<(() => void) | null>(null);

  const { listening, speaking, transcript, supported: voiceSupported, startListening, stopListening, speak } = useVoice({
    onTranscript: (text) => {
      setInput(text);
      setVoiceOverlay(false);
      stopListening();
    },
  });

  // Load agents + models on mount
  useEffect(() => {
    api.agents().then(setAgents).catch(console.error);
    api.models().then(setModels).catch(console.error);
  }, []);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, [input]);

  const handleNewChat = useCallback(() => {
    setChats((prev) => ({ ...prev, [selectedAgent]: [] }));
    sessionIds[selectedAgent] = `sess_${selectedAgent}_${Math.random().toString(36).slice(2, 10)}`;
    setInput("");
  }, [selectedAgent, sessionIds]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    const assistantMsg: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: "",
      agent: selectedAgent,
      model: selectedModel,
      timestamp: new Date(),
      streaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    let fullResponse = "";

    stopStreamRef.current = api.streamChat(
      { message: text, agent: selectedAgent, session_id: sessionId, model: selectedModel },
      (chunk) => {
        fullResponse += chunk;
        setMessages((prev) =>
          prev.map((m) => m.id === assistantMsg.id ? { ...m, content: fullResponse } : m)
        );
      },
      () => {
        setMessages((prev) =>
          prev.map((m) => m.id === assistantMsg.id ? { ...m, streaming: false } : m)
        );
        setLoading(false);
        if (speakResponses && fullResponse) speak(fullResponse.slice(0, 400));
      },
      (err) => {
        setMessages((prev) =>
          prev.map((m) => m.id === assistantMsg.id ? { ...m, content: `Error: ${err}`, streaming: false } : m)
        );
        setLoading(false);
      }
    );
  }, [input, loading, selectedAgent, selectedModel, sessionId, speakResponses, speak, setMessages]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleVoice = () => {
    if (listening) { stopListening(); setVoiceOverlay(false); }
    else { setVoiceOverlay(true); startListening(); }
  };

  // Welcome message
  const showWelcome = messages.length === 0;

  return (
    <div style={{ display: "flex", height: "100dvh", overflow: "hidden" }}>
      {/* Sidebar */}
      <Sidebar
        agents={agents}
        models={models}
        selectedAgent={selectedAgent}
        selectedModel={selectedModel}
        onSelectAgent={setSelectedAgent}
        onSelectModel={setSelectedModel}
        onNewChat={handleNewChat}
      />

      {/* Main chat area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative" }}>

        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "14px 24px", borderBottom: "1px solid var(--aios-border)",
          background: "rgba(10,10,20,0.8)", backdropFilter: "blur(20px)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontWeight: 700, textTransform: "capitalize", color: AGENT_COLORS[selectedAgent] || "var(--aios-accent)" }}>
              {selectedAgent} Agent
            </span>
            <span style={{ fontSize: "0.72rem", color: "var(--aios-text-3)", background: "var(--aios-surface)", padding: "2px 10px", borderRadius: "999px", border: "1px solid var(--aios-border)" }}>
              {selectedModel.split("/").pop()}
            </span>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {/* Multi-agent toggle */}
            <button
              className="btn-ghost"
              style={{ fontSize: "0.75rem", padding: "6px 12px", background: mode === "multi" ? "rgba(110,124,255,0.15)" : "transparent", color: mode === "multi" ? "var(--aios-accent)" : "var(--aios-text-2)" }}
              onClick={() => setMode(mode === "single" ? "multi" : "single")}
            >
              <Layers size={13} />
              {mode === "single" ? "Single" : "Multi"} Agent
            </button>

            {/* Speak toggle */}
            <button className="btn-icon" onClick={() => setSpeakResponses(!speakResponses)} title="Toggle voice responses">
              {speakResponses ? <Volume2 size={14} /> : <VolumeX size={14} />}
            </button>

            <button className="btn-icon" title="Settings">
              <Settings2 size={14} />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px" }}>
          {showWelcome ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", textAlign: "center", gap: 20 }}
            >
              <div style={{
                width: 72, height: 72, borderRadius: "50%",
                background: "linear-gradient(135deg, #6e7cff, #a78bfa)",
                display: "flex", alignItems: "center", justifyContent: "center",
                boxShadow: "0 0 40px rgba(110,124,255,0.4)",
              }}>
                <Zap size={32} color="white" />
              </div>
              <div>
                <h1 style={{ fontSize: "2rem", fontWeight: 800, letterSpacing: "-0.03em", marginBottom: 8 }}>
                  <span className="text-gradient">Hello, I'm AIOS</span>
                </h1>
                <p style={{ color: "var(--aios-text-2)", fontSize: "1rem", maxWidth: 480 }}>
                  Your personal AI Operating System. I can research, write code, browse the web, manage your memory, and analyze images.
                </p>
              </div>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "center", marginTop: 8 }}>
                {[
                  { label: "Research quantum computing", agent: "research" },
                  { label: "Write a Python web scraper", agent: "coding" },
                  { label: "What do I have saved in memory?", agent: "memory" },
                  { label: "Analyze my screen", agent: "vision" },
                ].map((s) => (
                  <button
                    key={s.label}
                    className="btn-ghost"
                    style={{ fontSize: "0.8rem" }}
                    onClick={() => {
                      setSelectedAgent(s.agent);
                      setInput(s.label);
                      textareaRef.current?.focus();
                    }}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </motion.div>
          ) : (
            <>
              {messages.map((msg) => (
                <MessageBubble key={msg.id} msg={msg} />
              ))}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="chat-input-container">
          <div className="chat-input-wrap">
            <textarea
              ref={textareaRef}
              className="chat-textarea"
              placeholder={`Message ${selectedAgent} agent… (Enter to send, Shift+Enter for newline)`}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
            />

            {voiceSupported && (
              <button
                className="btn-icon"
                onClick={handleVoice}
                style={{ border: "none", color: listening ? "var(--aios-accent)" : "var(--aios-text-3)" }}
                title={listening ? "Stop listening" : "Voice input"}
              >
                {listening ? <MicOff size={16} /> : <Mic size={16} />}
              </button>
            )}

            <button
              className="btn-icon"
              onClick={sendMessage}
              disabled={!input.trim() || loading}
              style={{
                background: input.trim() && !loading ? "var(--aios-accent)" : "transparent",
                color: input.trim() && !loading ? "white" : "var(--aios-text-3)",
                border: "none",
                cursor: input.trim() && !loading ? "pointer" : "not-allowed",
                transition: "all 0.2s",
              }}
            >
              {loading ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> : <Send size={16} />}
            </button>
          </div>

          <div style={{ display: "flex", justifyContent: "center", marginTop: 8, fontSize: "0.68rem", color: "var(--aios-text-3)" }}>
            AIOS v0.3 · {selectedAgent} · {selectedModel.split("/").pop()} ·{" "}
            {mode === "multi" ? "🔀 Multi-agent mode" : "📍 Single agent"}
          </div>
        </div>
      </div>

      {/* Voice Overlay */}
      <AnimatePresence>
        {voiceOverlay && (
          <motion.div
            className="voice-overlay"
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
          >
            <div className="voice-ring">
              <Mic size={24} color="white" />
            </div>
            <div style={{ fontSize: "0.9rem", fontWeight: 600 }}>Listening…</div>
            {transcript && <div style={{ fontSize: "0.82rem", color: "var(--aios-text-2)", maxWidth: 300, textAlign: "center" }}>{transcript}</div>}
            <button className="btn-ghost" onClick={() => { stopListening(); setVoiceOverlay(false); }}>
              Cancel
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
