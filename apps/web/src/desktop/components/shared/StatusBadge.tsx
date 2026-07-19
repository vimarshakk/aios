"use client";

interface StatusBadgeProps {
  label: string;
  status: "active" | "idle" | "warning" | "error" | "success";
  size?: "sm" | "md";
}

const STATUS_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  active: { bg: "rgba(224,94,56,0.12)", text: "#e05e38", dot: "#e05e38" },
  idle: { bg: "rgba(160,157,150,0.12)", text: "#a09d96", dot: "#a09d96" },
  warning: { bg: "rgba(245,158,11,0.12)", text: "#f59e0b", dot: "#f59e0b" },
  error: { bg: "rgba(239,68,68,0.12)", text: "#ef4444", dot: "#ef4444" },
  success: { bg: "rgba(16,185,129,0.12)", text: "#10b981", dot: "#10b981" },
};

export function StatusBadge({ label, status, size = "sm" }: StatusBadgeProps) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.idle;
  const isSmall = size === "sm";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: isSmall ? "4px" : "6px",
        padding: isSmall ? "2px 8px" : "4px 10px",
        borderRadius: "9999px",
        fontSize: isSmall ? "0.62rem" : "0.7rem",
        fontWeight: 500,
        background: colors.bg,
        color: colors.text,
      }}
    >
      <span
        style={{
          width: isSmall ? 5 : 6,
          height: isSmall ? 5 : 6,
          borderRadius: "50%",
          background: colors.dot,
          animation: status === "active" ? "pulse-dot 2s ease-in-out infinite" : undefined,
        }}
      />
      {label}
    </span>
  );
}
