"use client";

interface ProgressCardProps {
  label: string;
  progress: number; // 0-100
  status?: "running" | "completed" | "pending" | "error";
  detail?: string;
}

const STATUS_COLORS: Record<string, string> = {
  running: "var(--accent)",
  completed: "var(--success)",
  pending: "var(--text-muted)",
  error: "var(--danger)",
};

export function ProgressCard({ label, progress, status = "running", detail }: ProgressCardProps) {
  const color = STATUS_COLORS[status];

  return (
    <div style={{ padding: "12px 14px", borderRadius: "var(--radius-md)", background: "var(--surface)", border: "1px solid var(--border)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
        <span style={{ fontSize: "0.75rem", fontWeight: 500, color: "var(--text-primary)" }}>{label}</span>
        <span style={{ fontSize: "0.65rem", fontFamily: "var(--font-mono)", color }}>{Math.round(progress)}%</span>
      </div>
      <div style={{ height: 4, borderRadius: 2, background: "var(--surface-active)", overflow: "hidden" }}>
        <div
          style={{
            height: "100%",
            width: `${progress}%`,
            borderRadius: 2,
            background: color,
            transition: "width 0.6s ease",
            boxShadow: status === "running" ? `0 0 8px ${color}40` : undefined,
          }}
        />
      </div>
      {detail && (
        <p style={{ fontSize: "0.65rem", color: "var(--text-muted)", margin: "6px 0 0" }}>{detail}</p>
      )}
    </div>
  );
}
