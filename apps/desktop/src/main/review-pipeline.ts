/**
 * ReviewPipeline — AI reviews AI. Coordinates multi-step review flows.
 *
 * Pipeline stages:
 *   1. Author worker produces output (code, docs, etc.)
 *   2. Reviewer worker reviews the output (different model/CLI)
 *   3. If changes requested → author fixes → reviewer re-checks
 *   4. Verifier worker does a final verification pass
 *   5. Approver (Supervisor) gives final approval
 *
 * Provides:
 * - Review request creation and lifecycle
 * - Multi-stage pipeline (review → fix → verify → approve)
 * - Status tracking per review
 * - Persistent history
 */

import { EventEmitter } from "events";
import * as fs from "fs";
import * as path from "path";
import { app } from "electron";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ReviewStatus =
  | "pending"
  | "reviewing"
  | "changes-requested"
  | "fixing"
  | "verifying"
  | "approved"
  | "rejected"
  | "cancelled";

export type ReviewVerdict = "approve" | "changes" | "reject";

export interface ReviewNote {
  id: string;
  author: string; // worker ID or "system"
  content: string;
  timestamp: number;
  lineRef?: string; // e.g. "src/foo.ts:42"
}

export interface ReviewRequest {
  id: string;
  title: string;
  description: string;
  authorWorkerId: string;
  reviewerWorkerId?: string;
  verifierWorkerId?: string;
  status: ReviewStatus;
  outputSummary: string; // summary of the author's output
  outputFiles: string[]; // files changed/created
  reviewNotes: ReviewNote[];
  verdict?: ReviewVerdict;
  verdictReason?: string;
  fixRound: number;
  maxFixRounds: number;
  createdAt: number;
  updatedAt: number;
  completedAt?: number;
  metadata: Record<string, unknown>;
}

export interface ReviewPipelineState {
  totalReviews: number;
  pendingReviews: number;
  activeReviews: number;
  completedReviews: number;
  approvedReviews: number;
  rejectedReviews: number;
  avgReviewTimeMs: number;
}

// ---------------------------------------------------------------------------
// ReviewPipeline
// ---------------------------------------------------------------------------

export class ReviewPipeline extends EventEmitter {
  private reviews: Map<string, ReviewRequest> = new Map();
  private dataDir: string;
  private startTime: number;
  private idCounter = 0;

  constructor() {
    super();
    this.dataDir = path.join(app.getPath("userData"), "review-pipeline");
    this.ensureDataDir();
    this.startTime = Date.now();
    this.loadState();
  }

  // -- Lifecycle ------------------------------------------------------------

  private ensureDataDir(): void {
    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
    }
  }

  private loadState(): void {
    try {
      const reviewsPath = path.join(this.dataDir, "reviews.json");
      if (fs.existsSync(reviewsPath)) {
        const data = JSON.parse(fs.readFileSync(reviewsPath, "utf-8"));
        for (const r of data) {
          this.reviews.set(r.id, r);
        }
      }
    } catch { /* ignore */ }
  }

  private saveState(): void {
    try {
      const reviews = Array.from(this.reviews.values());
      fs.writeFileSync(
        path.join(this.dataDir, "reviews.json"),
        JSON.stringify(reviews, null, 2)
      );
    } catch (err) {
      console.error("[ReviewPipeline] Failed to save state:", err);
    }
  }

  private generateId(): string {
    return `review-${Date.now()}-${++this.idCounter}`;
  }

  private generateNoteId(): string {
    return `note-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  // -- Review lifecycle -----------------------------------------------------

  /**
   * Create a new review request.
   */
  createReview(
    title: string,
    description: string,
    authorWorkerId: string,
    outputSummary: string,
    outputFiles: string[],
    options?: {
      reviewerWorkerId?: string;
      verifierWorkerId?: string;
      maxFixRounds?: number;
      metadata?: Record<string, unknown>;
    }
  ): ReviewRequest {
    const review: ReviewRequest = {
      id: this.generateId(),
      title,
      description,
      authorWorkerId,
      reviewerWorkerId: options?.reviewerWorkerId,
      verifierWorkerId: options?.verifierWorkerId,
      status: "pending",
      outputSummary,
      outputFiles,
      reviewNotes: [],
      fixRound: 0,
      maxFixRounds: options?.maxFixRounds ?? 3,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      metadata: options?.metadata ?? {},
    };

    this.reviews.set(review.id, review);
    this.saveState();
    this.emit("review-created", review);
    return review;
  }

  /**
   * Assign a reviewer to a review.
   */
  assignReviewer(reviewId: string, reviewerWorkerId: string): boolean {
    const review = this.reviews.get(reviewId);
    if (!review || review.status !== "pending") return false;
    review.reviewerWorkerId = reviewerWorkerId;
    review.updatedAt = Date.now();
    this.saveState();
    this.emit("reviewer-assigned", { reviewId, reviewerWorkerId });
    return true;
  }

  /**
   * Start reviewing a review.
   */
  startReview(reviewId: string): boolean {
    const review = this.reviews.get(reviewId);
    if (!review || review.status !== "pending") return false;
    if (!review.reviewerWorkerId) return false;
    review.status = "reviewing";
    review.updatedAt = Date.now();
    this.saveState();
    this.emit("review-started", review);
    return true;
  }

  /**
   * Add a review note (comment/feedback).
   */
  addReviewNote(reviewId: string, author: string, content: string, lineRef?: string): ReviewNote | null {
    const review = this.reviews.get(reviewId);
    if (!review) return null;

    const note: ReviewNote = {
      id: this.generateNoteId(),
      author,
      content,
      timestamp: Date.now(),
      lineRef,
    };

    review.reviewNotes.push(note);
    review.updatedAt = Date.now();
    this.saveState();
    this.emit("review-note-added", { reviewId, note });
    return note;
  }

  /**
   * Submit a verdict (approve, request changes, reject).
   */
  submitVerdict(reviewId: string, verdict: ReviewVerdict, reason?: string): boolean {
    const review = this.reviews.get(reviewId);
    if (!review || review.status !== "reviewing") return false;

    review.verdict = verdict;
    review.verdictReason = reason;
    review.updatedAt = Date.now();

    switch (verdict) {
      case "approve":
        // Check if verifier is needed
        if (review.verifierWorkerId) {
          review.status = "verifying";
          this.emit("review-needs-verification", review);
        } else {
          review.status = "approved";
          review.completedAt = Date.now();
          this.emit("review-approved", review);
        }
        break;

      case "changes":
        if (review.fixRound >= review.maxFixRounds) {
          review.status = "rejected";
          review.completedAt = Date.now();
          this.emit("review-rejected", {
            review,
            reason: `Max fix rounds (${review.maxFixRounds}) exceeded`,
          });
        } else {
          review.status = "changes-requested";
          review.fixRound++;
          this.emit("review-changes-requested", review);
        }
        break;

      case "reject":
        review.status = "rejected";
        review.completedAt = Date.now();
        this.emit("review-rejected", { review, reason });
        break;
    }

    this.saveState();
    return true;
  }

  /**
   * Mark that author has applied fixes (transitions to verifying).
   */
  fixesApplied(reviewId: string, newOutputSummary: string, newFiles: string[]): boolean {
    const review = this.reviews.get(reviewId);
    if (!review || review.status !== "changes-requested") return false;

    review.outputSummary = newOutputSummary;
    review.outputFiles = newFiles;
    review.status = "reviewing"; // back to reviewer
    review.updatedAt = Date.now();
    this.saveState();
    this.emit("review-fixes-applied", review);
    return true;
  }

  /**
   * Complete verification.
   */
  completeVerification(reviewId: string, approved: boolean): boolean {
    const review = this.reviews.get(reviewId);
    if (!review || review.status !== "verifying") return false;

    review.status = approved ? "approved" : "rejected";
    review.completedAt = Date.now();
    review.updatedAt = Date.now();
    this.saveState();
    this.emit(approved ? "review-approved" : "review-rejected", { review });
    return true;
  }

  /**
   * Cancel a review.
   */
  cancelReview(reviewId: string): boolean {
    const review = this.reviews.get(reviewId);
    if (!review) return false;
    if (review.status === "approved" || review.status === "rejected" || review.status === "cancelled") {
      return false;
    }
    review.status = "cancelled";
    review.completedAt = Date.now();
    review.updatedAt = Date.now();
    this.saveState();
    this.emit("review-cancelled", review);
    return true;
  }

  // -- Queries --------------------------------------------------------------

  getReview(reviewId: string): ReviewRequest | undefined {
    return this.reviews.get(reviewId);
  }

  getAllReviews(): ReviewRequest[] {
    return Array.from(this.reviews.values());
  }

  getReviewsByStatus(status: ReviewStatus): ReviewRequest[] {
    return this.getAllReviews().filter((r) => r.status === status);
  }

  getReviewsByAuthor(workerId: string): ReviewRequest[] {
    return this.getAllReviews().filter((r) => r.authorWorkerId === workerId);
  }

  getReviewsByReviewer(workerId: string): ReviewRequest[] {
    return this.getAllReviews().filter((r) => r.reviewerWorkerId === workerId);
  }

  /**
   * Get active reviews (pending, reviewing, changes-requested, verifying).
   */
  getActiveReviews(): ReviewRequest[] {
    return this.getAllReviews().filter((r) =>
      ["pending", "reviewing", "changes-requested", "verifying"].includes(r.status)
    );
  }

  // -- State ----------------------------------------------------------------

  getState(): ReviewPipelineState {
    const reviews = this.getAllReviews();
    const completed = reviews.filter((r) => r.completedAt);
    const avgTime = completed.length > 0
      ? completed.reduce((sum, r) => sum + ((r.completedAt ?? 0) - r.createdAt), 0) / completed.length
      : 0;

    return {
      totalReviews: reviews.length,
      pendingReviews: reviews.filter((r) => r.status === "pending").length,
      activeReviews: reviews.filter((r) =>
        ["reviewing", "changes-requested", "verifying"].includes(r.status)
      ).length,
      completedReviews: completed.length,
      approvedReviews: reviews.filter((r) => r.status === "approved").length,
      rejectedReviews: reviews.filter((r) => r.status === "rejected").length,
      avgReviewTimeMs: Math.round(avgTime),
    };
  }

  destroy(): void {
    this.saveState();
  }
}

export default ReviewPipeline;
