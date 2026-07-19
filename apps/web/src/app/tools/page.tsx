"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Terminal, ArrowLeft, Settings, Shield, ShieldAlert, Cpu } from "lucide-react";
import { api, type ToolInfo } from "@/lib/api";
import Link from "next/link";

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.tools()
      .then((data) => {
        setTools(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const getCategoryColor = (cat: string) => {
    switch (cat.toLowerCase()) {
      case "utility": return "var(--aios-accent)";
      case "web": return "#06b6d4";
      case "execution": return "#10b981";
      case "filesystem": return "#a78bfa";
      case "memory": return "#ec4899";
      case "desktop": return "#f59e0b";
      default: return "var(--aios-text-3)";
    }
  };

  return (
    <div style={{ minHeight: "100dvh", background: "var(--aios-bg)", padding: "32px 40px" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 32 }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--aios-text-2)", textDecoration: "none", fontSize: "0.875rem" }}>
            <ArrowLeft size={16} /> Back to Chat
          </Link>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
          <div style={{ width: 40, height: 40, borderRadius: "50%", background: "linear-gradient(135deg, #10b981, #06b6d4)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Terminal size={18} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.03em" }}>Tools & Capabilities</h1>
            <p style={{ color: "var(--aios-text-2)", fontSize: "0.85rem" }}>Registered capabilities and tool functions available to agents</p>
          </div>
        </div>

        {loading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
            <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {tools.map((t, i) => {
              const catColor = getCategoryColor(t.category);
              const needsPermission = ["shell_execute", "filesystem", "screenshot"].includes(t.name);
              
              return (
                <motion.div
                  key={t.name}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="glass-card"
                  style={{ padding: "20px 24px" }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, marginBottom: 10 }}>
                    <div>
                      <h3 style={{ fontSize: "1.05rem", fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--aios-text)" }}>
                        {t.name}
                      </h3>
                      <span
                        style={{
                          display: "inline-block",
                          fontSize: "0.65rem",
                          padding: "2px 8px",
                          borderRadius: "999px",
                          background: `${catColor}15`,
                          color: catColor,
                          border: `1px solid ${catColor}30`,
                          fontWeight: 600,
                          textTransform: "uppercase",
                          marginTop: 6,
                        }}
                      >
                        {t.category}
                      </span>
                    </div>

                    <div style={{ display: "flex", gap: 8 }}>
                      {needsPermission ? (
                        <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.68rem", color: "var(--aios-yellow)", background: "rgba(245, 158, 11, 0.08)", padding: "4px 10px", borderRadius: "var(--r-sm)", border: "1px solid rgba(245, 158, 11, 0.2)" }}>
                          <ShieldAlert size={12} /> Needs Confirmation
                        </span>
                      ) : (
                        <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.68rem", color: "var(--aios-green)", background: "rgba(16, 185, 129, 0.08)", padding: "4px 10px", borderRadius: "var(--r-sm)", border: "1px solid rgba(16, 185, 129, 0.2)" }}>
                          <Shield size={12} /> Auto-allow
                        </span>
                      )}
                    </div>
                  </div>

                  <p style={{ fontSize: "0.85rem", color: "var(--aios-text-2)", lineHeight: 1.5 }}>
                    {t.description}
                  </p>

                  <div style={{ display: "flex", gap: 24, fontSize: "0.75rem", color: "var(--aios-text-3)", marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--aios-border)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <Settings size={12} />
                      <span>Interface: JSON Schema</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <Cpu size={12} />
                      <span>Type: Native Python Function</span>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
