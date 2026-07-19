"""AIOS Proactive Briefing engine (M5.5).

Generates a morning briefing objective from AIOS-native capabilities only
(notes, git, filesystem) and delivers a desktop notification summarising it.
No external integration is required (ADR-0022).

The briefing is *definitions-driven*: it inspects the platform's capability
resolver to decide which native sections to include, and falls back gracefully
when a local binary (git) is unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from aios.desktop.notifications import Notification, NotificationService, Urgency

logger = logging.getLogger("aios.supervisor.briefing")


@dataclass
class BriefingConfig:
    """Tuning for the proactive briefing."""

    title: str = "AIOS Briefing"
    # Local hour (24h) at/after which the daily briefing may run.
    after_hour: int = 7
    # Native sections to include when their capability is resolvable.
    sections: tuple[str, ...] = (
        "notes.review",
        "git.recent",
        "filesystem.reminders",
    )
    notify: bool = True


@dataclass
class BriefingEngine:
    """Compose and announce a daily briefing objective."""

    platform: object | None = None  # DeveloperPlatform (for capability resolution)
    config: BriefingConfig = field(default_factory=BriefingConfig)
    last_run_date: str = ""
    _notifier: NotificationService | None = field(default=None, repr=False)

    def today(self) -> str:
        return date.today().isoformat()  # noqa: DTZ011

    def _hour_ok(self) -> bool:
        from datetime import datetime

        return datetime.now().hour >= self.config.after_hour  # noqa: DTZ005

    def _capability_available(self, capability: str) -> bool:
        if self.platform is None:
            return False
        try:
            resolution = self.platform.resolve(capability)
        except Exception:  # noqa: BLE001  (resolver misconfigured -> skip section)
            return False
        return resolution.resolved

    def compose_objective(self) -> str | None:
        """Build the briefing goal text, or ``None`` if it shouldn't run now."""
        if not self._hour_ok():
            return None
        if self.today() == self.last_run_date:
            return None
        parts: list[str] = []
        if "notes.review" in self.config.sections and self._capability_available(
            "notes.read"
        ):
            parts.append("Summarize my notes from the past week")
        if "git.recent" in self.config.sections and self._capability_available(
            "git.status"
        ):
            parts.append("Summarize recent git activity across my projects")
        if "filesystem.reminders" in self.config.sections and self._capability_available(
            "filesystem.read"
        ):
            parts.append("Surface any stale or large files in Downloads")
        if not parts:
            # Even without sub-sections, a minimal check-in is useful.
            parts.append("Check system status and report anything urgent")
        return "Morning briefing: " + "; then ".join(parts)

    def mark_run(self, goal_id: str) -> None:
        """Record that today's briefing has been scheduled."""
        self.last_run_date = self.today()
        logger.info("Briefing scheduled as goal %s", goal_id)

    async def announce(self, summary: str) -> None:
        """Send the briefing notification (no-op if notifications unavailable)."""
        if not self.config.notify:
            return
        notifier = self._notifier or NotificationService()
        self._notifier = notifier
        result = await notifier.send(
            Notification(
                title=self.config.title,
                body=summary[:240],
                urgency=Urgency.NORMAL,
                app_name="AIOS",
            )
        )
        if not result.ok:
            logger.info("Briefing notification unavailable: %s", result.error)


__all__ = ["BriefingConfig", "BriefingEngine"]
