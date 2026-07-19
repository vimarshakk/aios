"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { api } from "@/lib/api";
import { CommandBar } from "../components/CommandBar";
import { GoalProgressCard } from "../components/GoalProgressCard";
import {
  Loader2, Bot, User, Sparkles, RotateCcw, Wrench, XCircle,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Message types
// ---------------------------------------------------------------------------

interface ToolEvent {
  name: string;
  status: "running" | "done";
  success?: boolean;
}

interface GoalRef {
  goalId: string;
  objective: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: string;
  model?: string;
  timestamp: number;
  streaming?: boolean;
  error?: boolean;
  tools?: ToolEvent[];
  goal?: GoalRef;
}

// ---------------------------------------------------------------------------
// Conversation Workspace — the heart of AIOS
// ---------------------------------------------------------------------------

export function ConversationWorkspace() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, streaming]);

  const handleExecute = useCallback((text: string, opts: { agent: string; model?: string }) => {
    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: Date.now(),
    };
    const assistantId = `a-${Date.now()}`;
    const assistantMsg: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      agent: opts.agent,
      model: opts.model,
      timestamp: Date.now(),
      streaming: true,
      tools: [],
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setCurrentId(assistantId);
    setStreaming(true);

    let accumulated = "";

    const cancel = api.streamChat(
      { message: text, agent: opts.agent, model: opts.model || undefined },
      (chunk) => {
        accumulated += chunk;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: accumulated } : m,
          ),
        );
      },
      () => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, streaming: false } : m,
          ),
        );
        setStreaming(false);
        setCurrentId(null);
      },
      (err) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: accumulated || `Error: ${err}`, streaming: false, error: !accumulated }
              : m,
          ),
        );
        setStreaming(false);
        setCurrentId(null);
      },
      {
        onToolCall: (tool) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, tools: [...(m.tools ?? []), { name: tool.name, status: "running" as const }] }
                : m,
            ),
          );
        },
        onToolResult: (tool, success) => {
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== assistantId) return m;
              const tools = (m.tools ?? []).map((t) =>
                t.name === tool && t.status === "running"
                  ? { ...t, status: "done" as const, success }
                  : t,
              );
              return { ...m, tools };
            }),
          );
        },
      },
    );

    abortRef.current = cancel;
  }, []);

  // Chat → Goal: submit an objective and render a live progress card.
  // Plain function — React Compiler auto-memoizes (avoids preserve-manual-memoization error).
  const handleCreateGoal = (text: string) => {
    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg, {
      id: `g-${Date.now()}`,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
    }]);

    api.createGoal({ objective: text })
      .then((res) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id.startsWith("g-") && m.content === "" && !m.goal
              ? { ...m, goal: { goalId: res.goal_id, objective: text } }
              : m,
          ),
        );
      })
      .catch((err) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id.startsWith("g-") && m.content === "" && !m.goal
              ? { ...m, content: `Failed to create goal: ${err}`, error: true }
              : m,
          ),
        );
      });
  };

  // Handle pending message / goal from other workspaces (via CommandBar).
  // Declared after the handlers it references to avoid TDZ / lint "used before declared".
  useEffect(() => {
    const pending = sessionStorage.getItem("aios-pending-message");
    if (pending) {
      sessionStorage.removeItem("aios-pending-message");
      const timer = setTimeout(() => handleExecute(pending, { agent: "default", model: "" }), 100);
      return () => clearTimeout(timer);
    }
    const pendingGoal = sessionStorage.getItem("aios-pending-goal");
    if (pendingGoal) {
      sessionStorage.removeItem("aios-pending-goal");
      const timer = setTimeout(() => handleCreateGoal(pendingGoal), 100);
      return () => clearTimeout(timer);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleStop = useCallback(() => {
    abortRef.current?.();
    setStreaming(false);
    setCurrentId(null);
    setMessages((prev) =>
      prev.map((m) =>
        m.id === currentId ? { ...m, streaming: false } : m,
      ),
    );
  }, [currentId]);

  const handleRetry = useCallback((idx: number) => {
    const userMsg = messages[idx];
    if (!userMsg || userMsg.role !== "user") return;
    // Remove the failed assistant message and re-send
    setMessages((prev) => prev.slice(0, idx + 1));
    handleExecute(userMsg.content, { agent: "default", model: "" });
  }, [messages, handleExecute]);

  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {!hasMessages ? (
          <EmptyState />
        ) : (
          <div className="max-w-3xl mx-auto px-6 py-6">
            {messages.map((msg, idx) => (
              <div key={msg.id}>
                <MessageBubble
                  msg={msg}
                  onRetry={
                    msg.role === "assistant" && !msg.streaming && msg.error
                      ? () => handleRetry(idx - 1)
                      : undefined
                  }
                />
                {msg.goal && (
                  <GoalProgressCard goalId={msg.goal.goalId} objective={msg.goal.objective} />
                )}
              </div>
            ))}
            {streaming && messages[messages.length - 1]?.streaming && (
              <div className="flex items-center gap-2 py-2">
                <Loader2 size={14} className="animate-spin" style={{ color: "var(--accent)" }} />
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>Thinking…</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Command bar — persistent at bottom */}
      <CommandBar
        onExecute={handleExecute}
        onGoal={handleCreateGoal}
        streaming={streaming}
        onStop={handleStop}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty state — greeting screen
// ---------------------------------------------------------------------------

function EmptyState() {
  const suggestions = [
    { icon: "🔍", text: "Review my repository" },
    { icon: "🎯", text: "Create a new goal" },
    { icon: "📝", text: "Summarize today's work" },
    { icon: "🐛", text: "Find and fix bugs" },
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 px-8">
      {/* Logo */}
      <div
        className="w-14 h-14 rounded-2xl flex items-center justify-center"
        style={{ background: "var(--accent-glow)", color: "var(--accent)" }}
      >
        <Sparkles size={24} />
      </div>

      {/* Greeting */}
      <div className="text-center">
        <h1 className="text-xl font-semibold mb-1" style={{ color: "var(--text-primary)" }}>
          Good {getTimeOfDay()}. I&apos;m AIOS.
        </h1>
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
          What would you like to accomplish today?
        </p>
      </div>

      {/* Quick suggestions */}
      <div className="flex flex-wrap justify-center gap-2 mt-2">
        {suggestions.map((s) => (
          <button
            key={s.text}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-all"
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              color: "var(--text-secondary)",
              cursor: "pointer",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--accent)";
              e.currentTarget.style.color = "var(--text-primary)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.color = "var(--text-secondary)";
            }}
          >
            <span>{s.icon}</span>
            {s.text}
          </button>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------

function MessageBubble({
  msg,
  onRetry,
}: {
  msg: Message;
  onRetry?: () => void;
}) {
  const isUser = msg.role === "user";

  return (
    <div className={`flex gap-3 mb-5 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5"
          style={{ background: "var(--accent-glow)", color: "var(--accent)", border: "1px solid var(--accent)" }}
        >
          <Bot size={14} />
        </div>
      )}

      <div
        className={`max-w-[85%] ${isUser ? "order-first" : ""}`}
      >
        {/* Content */}
        <div
          className={`rounded-xl px-4 py-3 text-[0.88rem] leading-relaxed ${
            isUser ? "rounded-br-sm" : "rounded-bl-sm"
          }`}
          style={{
            background: isUser ? "var(--surface-active)" : "transparent",
            border: isUser ? "1px solid var(--border-strong)" : "none",
            color: "var(--text-primary)",
          }}
        >
          {isUser ? (
            <span className="whitespace-pre-wrap">{msg.content}</span>
          ) : (
            <div className="prose">
              <ReactMarkdown
                components={{
                  code({ className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    const codeStr = String(children).replace(/\n$/, "");
                    if (match) {
                      return (
                        <SyntaxHighlighter
                          style={oneDark}
                          language={match[1]}
                          PreTag="div"
                          customStyle={{
                            borderRadius: "var(--radius-md)",
                            fontSize: "0.82em",
                            margin: "8px 0",
                          }}
                        >
                          {codeStr}
                        </SyntaxHighlighter>
                      );
                    }
                    return (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  },
                }}
              >
                {msg.content}
              </ReactMarkdown>

              {/* Tool execution timeline */}
              {msg.tools && msg.tools.length > 0 && (
                <div className="flex flex-col gap-1 mt-2 pl-1">
                  {msg.tools.map((t, i) => (
                    <div key={`${t.name}-${i}`} className="flex items-center gap-1.5">
                      {t.status === "running" ? (
                        <Loader2 size={11} className="animate-spin" style={{ color: "var(--accent)" }} />
                      ) : t.success === false ? (
                        <XCircle size={11} style={{ color: "var(--danger)" }} />
                      ) : (
                        <Wrench size={11} style={{ color: "var(--success)" }} />
                      )}
                      <span
                        className="text-[0.62rem] font-mono"
                        style={{
                          color:
                            t.status === "running"
                              ? "var(--text-secondary)"
                              : t.success === false
                                ? "var(--danger)"
                                : "var(--text-muted)",
                        }}
                      >
                        {t.name}
                        {t.status === "running" ? "…" : ""}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Meta */}
        <div className="flex items-center gap-2 mt-1 px-1">
          <span className="text-[0.6rem]" style={{ color: "var(--text-muted)" }}>
            {formatTime(msg.timestamp)}
          </span>
          {msg.agent && msg.agent !== "default" && (
            <span
              className="text-[0.55rem] px-1.5 py-0.5 rounded"
              style={{ background: "var(--surface)", color: "var(--accent)" }}
            >
              {msg.agent}
            </span>
          )}
          {onRetry && (
            <button
              className="flex items-center gap-1 text-[0.6rem] transition-colors"
              style={{ color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer" }}
              onClick={onRetry}
            >
              <RotateCcw size={10} />
              Retry
            </button>
          )}
        </div>
      </div>

      {isUser && (
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5"
          style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
        >
          <span style={{ color: "var(--text-secondary)" }}><User size={14} /></span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getTimeOfDay(): string {
  const h = new Date().getHours();
  if (h < 12) return "morning";
  if (h < 17) return "afternoon";
  return "evening";
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
