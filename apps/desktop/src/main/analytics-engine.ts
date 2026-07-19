/**
 * AnalyticsEngine — Usage analytics and productivity insights.
 *
 * Provides:
 * - Session tracking (start, end, duration)
 * - Feature usage tracking
 * - Productivity scoring
 * - Usage patterns and trends
 * - Privacy-first: all data stored locally
 */

import { EventEmitter } from "events";
import * as fs from "fs";
import * as path from "path";
import { app } from "electron";

export interface Session {
  id: string;
  startTime: number;
  endTime?: number;
  duration?: number;
  feature: string;
  action: string;
  metadata?: Record<string, unknown>;
}

export interface FeatureUsage {
  feature: string;
  count: number;
  totalTime: number;
  lastUsed: number;
  trend: "increasing" | "decreasing" | "stable";
}

export interface ProductivityScore {
  overall: number; // 0-100
  sessionCount: number;
  avgSessionDuration: number;
  featuresUsed: number;
  mostUsedFeature: string;
  peakHour: number;
  streak: number; // days
}

export interface UsagePattern {
  hour: number;
  dayOfWeek: number;
  count: number;
  avgDuration: number;
}

export interface AnalyticsSnapshot {
  totalSessions: number;
  totalTime: number;
  totalFeatures: number;
  sessionsToday: number;
  timeToday: number;
  topFeatures: FeatureUsage[];
  productivity: ProductivityScore;
  patterns: UsagePattern[];
}

export class AnalyticsEngine extends EventEmitter {
  private sessions: Session[] = [];
  private featureUsage: Map<string, FeatureUsage> = new Map();
  private patterns: Map<string, UsagePattern> = new Map();
  private currentSession: Session | null = null;
  private dataDir: string;
  private maxSessions = 10000;

  constructor() {
    super();
    this.dataDir = path.join(app.getPath("userData"), "analytics");
    this.ensureDataDir();
    this.loadLocalData();
  }

  /**
   * Ensure analytics data directory exists.
   */
  private ensureDataDir(): void {
    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
    }
  }

  /**
   * Load analytics data from disk.
   */
  private loadLocalData(): void {
    try {
      const sessionsPath = path.join(this.dataDir, "sessions.json");
      if (fs.existsSync(sessionsPath)) {
        this.sessions = JSON.parse(fs.readFileSync(sessionsPath, "utf-8"));
      }

      const featuresPath = path.join(this.dataDir, "features.json");
      if (fs.existsSync(featuresPath)) {
        const data = JSON.parse(fs.readFileSync(featuresPath, "utf-8"));
        for (const [key, value] of Object.entries(data)) {
          this.featureUsage.set(key, value as FeatureUsage);
        }
      }

      const patternsPath = path.join(this.dataDir, "patterns.json");
      if (fs.existsSync(patternsPath)) {
        const data = JSON.parse(fs.readFileSync(patternsPath, "utf-8"));
        for (const [key, value] of Object.entries(data)) {
          this.patterns.set(key, value as UsagePattern);
        }
      }
    } catch { /* ignore */ }
  }

  /**
   * Save analytics data to disk.
   */
  private saveLocalData(): void {
    try {
      fs.writeFileSync(
        path.join(this.dataDir, "sessions.json"),
        JSON.stringify(this.sessions.slice(-this.maxSessions), null, 2)
      );

      const featuresData: Record<string, FeatureUsage> = {};
      for (const [key, value] of this.featureUsage) {
        featuresData[key] = value;
      }
      fs.writeFileSync(path.join(this.dataDir, "features.json"), JSON.stringify(featuresData, null, 2));

      const patternsData: Record<string, UsagePattern> = {};
      for (const [key, value] of this.patterns) {
        patternsData[key] = value;
      }
      fs.writeFileSync(path.join(this.dataDir, "patterns.json"), JSON.stringify(patternsData, null, 2));
    } catch (err) {
      console.error("[Analytics] Failed to save data:", err);
    }
  }

  /**
   * Start tracking a session.
   */
  startSession(feature: string, action: string, metadata?: Record<string, unknown>): Session {
    // End current session if any
    if (this.currentSession) {
      this.endSession();
    }

    const session: Session = {
      id: `session-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      startTime: Date.now(),
      feature,
      action,
      metadata,
    };

    this.currentSession = session;
    this.sessions.push(session);

    // Update feature usage
    this.updateFeatureUsage(feature);

    // Update patterns
    this.updatePatterns();

    this.emit("session-started", session);
    return session;
  }

  /**
   * End the current session.
   */
  endSession(): Session | null {
    if (!this.currentSession) return null;

    const session = this.currentSession;
    session.endTime = Date.now();
    session.duration = session.endTime - session.startTime;

    this.currentSession = null;
    this.saveLocalData();

    this.emit("session-ended", session);
    return session;
  }

  /**
   * Track a feature event (without session lifecycle).
   */
  trackEvent(feature: string, action: string, metadata?: Record<string, unknown>): void {
    const session: Session = {
      id: `event-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      startTime: Date.now(),
      endTime: Date.now(),
      duration: 0,
      feature,
      action,
      metadata,
    };

    this.sessions.push(session);
    this.updateFeatureUsage(feature);
    this.updatePatterns();
    this.emit("event-tracked", session);
  }

  /**
   * Update feature usage stats.
   */
  private updateFeatureUsage(feature: string): void {
    const existing = this.featureUsage.get(feature);
    const now = Date.now();

    if (existing) {
      existing.count++;
      existing.lastUsed = now;
    } else {
      this.featureUsage.set(feature, {
        feature,
        count: 1,
        totalTime: 0,
        lastUsed: now,
        trend: "stable",
      });
    }
  }

  /**
   * Update usage patterns.
   */
  private updatePatterns(): void {
    const now = new Date();
    const hour = now.getHours();
    const dayOfWeek = now.getDay();
    const key = `${hour}-${dayOfWeek}`;

    const existing = this.patterns.get(key);
    if (existing) {
      existing.count++;
    } else {
      this.patterns.set(key, {
        hour,
        dayOfWeek,
        count: 1,
        avgDuration: 0,
      });
    }
  }

  /**
   * Get all sessions.
   */
  getSessions(limit = 100): Session[] {
    return this.sessions.slice(-limit);
  }

  /**
   * Get sessions for a specific feature.
   */
  getSessionsByFeature(feature: string): Session[] {
    return this.sessions.filter((s) => s.feature === feature);
  }

  /**
   * Get feature usage stats.
   */
  getFeatureUsage(): FeatureUsage[] {
    return Array.from(this.featureUsage.values()).sort((a, b) => b.count - a.count);
  }

  /**
   * Get usage patterns.
   */
  getPatterns(): UsagePattern[] {
    return Array.from(this.patterns.values());
  }

  /**
   * Calculate productivity score.
   */
  getProductivityScore(): ProductivityScore {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayTimestamp = today.getTime();

    const sessionsToday = this.sessions.filter(
      (s) => s.startTime >= todayTimestamp
    );

    const totalTimeToday = sessionsToday.reduce((sum, s) => sum + (s.duration || 0), 0);
    const totalTime = this.sessions.reduce((sum, s) => sum + (s.duration || 0), 0);

    const featuresUsed = this.featureUsage.size;
    const topFeature = this.getFeatureUsage()[0];

    // Find peak hour
    const hourCounts = new Array(24).fill(0);
    for (const pattern of this.patterns.values()) {
      hourCounts[pattern.hour] += pattern.count;
    }
    const peakHour = hourCounts.indexOf(Math.max(...hourCounts));

    // Calculate streak (simplified: consecutive days with sessions)
    let streak = 0;
    const dayMs = 86400000;
    const checkDate = new Date();
    while (true) {
      const dayStart = new Date(checkDate);
      dayStart.setHours(0, 0, 0, 0);
      const dayEnd = new Date(checkDate);
      dayEnd.setHours(23, 59, 59, 999);

      const hasSessions = this.sessions.some(
        (s) => s.startTime >= dayStart.getTime() && s.startTime <= dayEnd.getTime()
      );

      if (!hasSessions) break;
      streak++;
      checkDate.setDate(checkDate.getDate() - 1);
    }

    // Overall score (0-100)
    const sessionScore = Math.min(30, sessionsToday.length * 3);
    const timeScore = Math.min(30, totalTimeToday / 60000); // 1 point per minute, max 30
    const featureScore = Math.min(20, featuresUsed * 2);
    const streakScore = Math.min(20, streak * 4);

    const overall = Math.round(sessionScore + timeScore + featureScore + streakScore);

    return {
      overall: Math.min(100, overall),
      sessionCount: this.sessions.length,
      avgSessionDuration: this.sessions.length
        ? totalTime / this.sessions.length
        : 0,
      featuresUsed,
      mostUsedFeature: topFeature?.feature || "none",
      peakHour,
      streak,
    };
  }

  /**
   * Get a full analytics snapshot.
   */
  getSnapshot(): AnalyticsSnapshot {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayTimestamp = today.getTime();

    const sessionsToday = this.sessions.filter(
      (s) => s.startTime >= todayTimestamp
    );
    const timeToday = sessionsToday.reduce((sum, s) => sum + (s.duration || 0), 0);
    const totalTime = this.sessions.reduce((sum, s) => sum + (s.duration || 0), 0);

    return {
      totalSessions: this.sessions.length,
      totalTime,
      totalFeatures: this.featureUsage.size,
      sessionsToday: sessionsToday.length,
      timeToday,
      topFeatures: this.getFeatureUsage().slice(0, 10),
      productivity: this.getProductivityScore(),
      patterns: this.getPatterns(),
    };
  }

  /**
   * Clear all analytics data.
   */
  clearAll(): void {
    this.sessions = [];
    this.featureUsage.clear();
    this.patterns.clear();
    this.currentSession = null;
    this.saveLocalData();
    this.emit("analytics-cleared");
  }

  /**
   * Destroy the analytics engine.
   */
  destroy(): void {
    this.endSession();
    this.saveLocalData();
  }
}

export default AnalyticsEngine;
