"use client";

import { useState, useEffect, useCallback } from "react";
import { ReviewPanel } from "../components/devmode/ReviewPanel";
import { api } from "@/lib/api";
import type { ReviewRequest } from "../types";
import { CheckCircle2, Eye, Clock } from "lucide-react";

export function ReviewsWorkspace() {
  const [reviews, setReviews] = useState<ReviewRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await api.reviews.listActive();
      const allRes = await api.reviews.getState();
      const activeList = Array.isArray(res) ? res : [];
      const allList = (allRes as Record<string, unknown>)?.reviews
        ? ((allRes as Record<string, unknown>).reviews as Record<string, unknown>[])
        : activeList;

      const mapped: ReviewRequest[] = allList.map((r: Record<string, unknown>) => ({
        id: r.id as string,
        taskId: "",
        taskName: (r.title as string) || "",
        sourceWorker: (r.authorWorkerId as string) || "",
        reviewWorker: (r.reviewerWorkerId as string) || "",
        sourceOutput: (r.outputSummary as string) || "",
        status: (r.status as string) as ReviewRequest["status"],
        reviewNotes: (r.verdictReason as string) || "",
        createdAt: (r.createdAt as number) || Date.now(),
        completedAt: r.completedAt as number | undefined,
      }));
      setReviews(mapped);
      setLoading(false);
      setError(null);
    } catch (e) {
      setError(String(e));
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)" }}>
        <span style={{ fontSize: "0.85rem" }}>Loading reviews...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)", gap: "8px" }}>
        <span style={{ fontSize: "0.85rem" }}>Could not load reviews</span>
        <span style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>{error}</span>
        <button onClick={fetchData} style={{ marginTop: "8px", padding: "6px 14px", borderRadius: "6px", background: "var(--accent)", color: "#fff", border: "none", fontSize: "0.75rem", cursor: "pointer" }}>Retry</button>
      </div>
    );
  }

  const approved = reviews.filter((r) => r.status === "approved").length;
  const pending = reviews.filter((r) => r.status === "pending" || r.status === "running").length;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", borderBottom: "1px solid var(--border)", background: "var(--bg-subtle)", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ color: "var(--accent)", display: "inline-flex" }}><Eye size={16} /></span>
          <span style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-primary)" }}>Reviews</span>
          <span style={{ fontSize: "0.65rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", padding: "2px 6px", borderRadius: "4px", background: "var(--surface)", color: "var(--text-muted)" }}>
            {approved} approved · {pending} pending
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "0.72rem", color: "var(--text-secondary)" }}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}><CheckCircle2 size={12} />{approved} approved</span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}><Clock size={12} />{pending} pending</span>
        </div>
      </div>

      {/* Review content */}
      <div style={{ flex: 1, overflow: "auto" }}>
        <ReviewPanel reviews={reviews} />
      </div>
    </div>
  );
}

export default ReviewsWorkspace;
