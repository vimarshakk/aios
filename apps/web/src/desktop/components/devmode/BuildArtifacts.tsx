"use client";

import { useState, useMemo } from "react";
import type { BuildArtifact } from "../../types";
import {
  FileText, Folder, TestTube, Settings, Rocket, CheckCircle2,
  Trash2, Edit, Minus, ChevronRight, ChevronDown, Search,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Status config
// ---------------------------------------------------------------------------

const STATUS_CONFIG: Record<string, { icon: React.ComponentType<{ size?: number }>; color: string }> = {
  generated: { icon: CheckCircle2, color: "var(--green)" },
  modified: { icon: Edit, color: "#f59e0b" },
  deleted: { icon: Trash2, color: "#ef4444" },
  unchanged: { icon: Minus, color: "var(--text-muted)" },
};

const TYPE_ICONS: Record<string, React.ComponentType<{ size?: number }>> = {
  file: FileText,
  directory: Folder,
  test: TestTube,
  config: Settings,
  deployment: Rocket,
};

// ---------------------------------------------------------------------------
// File tree node
// ---------------------------------------------------------------------------

interface TreeNode {
  name: string;
  path: string;
  type: "file" | "directory";
  artifact?: BuildArtifact;
  children: TreeNode[];
}

function buildTree(artifacts: BuildArtifact[]): TreeNode[] {
  const root: TreeNode[] = [];

  for (const a of artifacts) {
    const parts = a.path.split("/");
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;
      let existing = current.find((n) => n.name === part);

      if (!existing) {
        existing = {
          name: part,
          path: parts.slice(0, i + 1).join("/"),
          type: isLast ? (a.type === "directory" ? "directory" : "file") : "directory",
          artifact: isLast ? a : undefined,
          children: [],
        };
        current.push(existing);
      }

      if (!isLast) {
        current = existing.children;
      }
    }
  }

  return root;
}

// ---------------------------------------------------------------------------
// Tree node component
// ---------------------------------------------------------------------------

function TreeNodeView({ node, depth }: { node: TreeNode; depth: number }) {
  const [expanded, setExpanded] = useState(depth < 2);
  const isDir = node.type === "directory";
  const Icon = isDir ? Folder : (TYPE_ICONS[node.artifact?.type ?? "file"] ?? FileText);
  const statusCfg = node.artifact ? STATUS_CONFIG[node.artifact.status] : null;
  const StatusIcon = statusCfg?.icon;

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          padding: "4px 8px",
          paddingLeft: `${depth * 16 + 8}px`,
          cursor: "pointer",
          borderRadius: "var(--radius-sm)",
          transition: "background 0.1s ease",
        }}
        onClick={() => isDir && setExpanded(!expanded)}
        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-hover)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "none")}
      >
        {isDir ? (
          expanded
            ? <span style={{ color: "var(--text-muted)", display: "inline-flex" }}><ChevronDown size={12} /></span>
            : <span style={{ color: "var(--text-muted)", display: "inline-flex" }}><ChevronRight size={12} /></span>
        ) : (
          <span style={{ width: 12 }} />
        )}
        <span style={{ color: isDir ? "#f59e0b" : "var(--text-secondary)", flexShrink: 0, display: "inline-flex" }}>
          <Icon size={14} />
        </span>
        <span
          style={{
            fontSize: "0.78rem",
            color: "var(--text-primary)",
            fontFamily: isDir ? "inherit" : "var(--font-mono)",
            fontWeight: isDir ? 500 : 400,
            flex: 1,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {node.name}
        </span>
        {node.artifact?.workerId && (
          <span
            style={{
              fontSize: "0.6rem",
              padding: "1px 5px",
              borderRadius: "9999px",
              background: "var(--surface)",
              color: "var(--text-muted)",
              border: "1px solid var(--border)",
            }}
          >
            {node.artifact.workerId}
          </span>
        )}
        {StatusIcon && statusCfg && (
          <span style={{ color: statusCfg.color, flexShrink: 0, display: "inline-flex" }}>
            <StatusIcon size={12} />
          </span>
        )}
      </div>
      {isDir && expanded && (
        <div>
          {node.children.map((child) => (
            <TreeNodeView key={child.path} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// BuildArtifacts
// ---------------------------------------------------------------------------

export function BuildArtifacts({ artifacts }: { artifacts: BuildArtifact[] }) {
  const [search, setSearch] = useState("");
  const tree = useMemo(() => buildTree(artifacts), [artifacts]);

  const filtered = search
    ? artifacts.filter((a) => a.path.toLowerCase().includes(search.toLowerCase()))
    : artifacts;

  const stats = {
    total: artifacts.length,
    generated: artifacts.filter((a) => a.status === "generated").length,
    modified: artifacts.filter((a) => a.status === "modified").length,
    deleted: artifacts.filter((a) => a.status === "deleted").length,
  };

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "12px", height: "100%" }}>
      {/* Summary */}
      <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
        <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-primary)" }}>
          Build Artifacts
        </span>
        <span style={{ fontSize: "0.72rem", color: "var(--text-secondary)" }}>
          {stats.total} files · {stats.generated} generated · {stats.modified} modified · {stats.deleted} deleted
        </span>
      </div>

      {/* Search */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "6px 10px",
          borderRadius: "var(--radius-sm)",
          background: "var(--surface)",
          border: "1px solid var(--border)",
        }}
      >
        <span style={{ color: "var(--text-muted)", display: "inline-flex" }}>
          <Search size={14} />
        </span>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search artifacts..."
          style={{
            flex: 1,
            background: "none",
            border: "none",
            outline: "none",
            color: "var(--text-primary)",
            fontSize: "0.78rem",
          }}
        />
      </div>

      {/* File tree */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--border)",
          background: "var(--bg-subtle)",
          padding: "4px 0",
        }}
      >
        {search ? (
          filtered.map((a) => {
            const Icon = TYPE_ICONS[a.type] ?? FileText;
            const statusCfg = STATUS_CONFIG[a.status];
            const StatusIcon = statusCfg?.icon;
            return (
              <div
                key={a.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "6px 12px",
                  cursor: "pointer",
                }}
              >
                <span style={{ color: "var(--text-secondary)", display: "inline-flex" }}>
                  <Icon size={14} />
                </span>
                <span style={{ fontSize: "0.78rem", fontFamily: "var(--font-mono)", color: "var(--text-primary)", flex: 1 }}>
                  {a.path}
                </span>
                {StatusIcon && statusCfg && (
                  <span style={{ color: statusCfg.color, display: "inline-flex" }}>
                    <StatusIcon size={12} />
                  </span>
                )}
              </div>
            );
          })
        ) : (
          tree.map((node) => (
            <TreeNodeView key={node.path} node={node} depth={0} />
          ))
        )}
      </div>
    </div>
  );
}
