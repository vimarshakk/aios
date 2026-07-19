"""AIOS Daemon — long-running supervisor host (M5.3).

The daemon keeps a :class:`Supervisor` alive across the process lifetime,
optionally persists goal state to disk so goals survive restarts, and runs a
scheduler for proactive goals (e.g. the morning briefing from M5.5).

Design constraints (ADR-0022):
- Fully offline: the daemon and its scheduler only use AIOS-native skills.
- No external integration is required; ``composio``/MCP are optional providers
  the resolver may prefer when connected, never a dependency.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .supervisor import Supervisor

if TYPE_CHECKING:
    from aios.platform import DeveloperPlatform

    from .briefing import BriefingEngine

logger = logging.getLogger("aios.supervisor.daemon")

ApprovalCallback = Callable[[Any], Awaitable[bool]]


@dataclass
class DaemonConfig:
    """Configuration for the AIOS daemon."""

    data_dir: str = "~/.aios/daemon"
    persist: bool = True
    briefing: BriefingEngine | None = None
    # Seconds between scheduler ticks (briefing checks). Default: 60s.
    tick_seconds: int = 60


class Daemon:
    """Background host for the Supervisor with persistence and scheduling."""

    def __init__(
        self,
        platform: DeveloperPlatform,
        config: DaemonConfig | None = None,
        *,
        approval_callback: ApprovalCallback | None = None,
        require_approval: bool = True,
    ) -> None:
        self._platform = platform
        self.config = config or DaemonConfig()
        self.supervisor = Supervisor(
            platform,
            approval_callback=approval_callback,
            require_approval=require_approval,
            on_goal_update=lambda _: self._save() if self.config.persist else None,
        )
        self._briefing = self.config.briefing
        self._stop = asyncio.Event()
        self._tick = self.config.tick_seconds
        self._data_path = self._resolve_data_path()
        self.started_at = time.monotonic()
        if self.config.persist:
            self._load()

    # -------------------------------------------------------------- lifecycle

    async def start(self) -> None:
        """Start the daemon's scheduler loop. Runs until ``stop()``."""
        logger.info("AIOS daemon started (persist=%s)", self.config.persist)
        if self.config.persist:
            self._save()
        try:
            while not self._stop.is_set():
                await self._maybe_briefing()
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self._tick)
                except TimeoutError:
                    continue
        finally:
            if self.config.persist:
                self._save()
            logger.info("AIOS daemon stopped")

    async def stop(self) -> None:
        """Signal the daemon to stop (and persist state)."""
        self._stop.set()
        if self.config.persist:
            self._save()

    def run_forever(self) -> None:
        """Blocking helper used by the ``aiosd`` console script."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        asyncio.run(self.start())

    # ----------------------------------------------------------------- passthru

    async def submit(self, objective: str, **kw: Any) -> str:
        """Submit a goal; returns the goal id."""
        goal = await self.supervisor.submit(objective, **kw)
        if self.config.persist:
            self._save()
        return goal.goal_id

    async def pause(self, goal_id: str) -> bool:
        ok = await self.supervisor.pause(goal_id)
        if ok and self.config.persist:
            self._save()
        return ok

    async def resume(self, goal_id: str) -> bool:
        ok = await self.supervisor.resume(goal_id)
        if ok and self.config.persist:
            self._save()
        return ok

    async def cancel(self, goal_id: str) -> bool:
        ok = await self.supervisor.cancel(goal_id)
        if ok and self.config.persist:
            self._save()
        return ok

    def status(self) -> dict[str, Any]:
        return {
            "uptime_seconds": round(time.monotonic() - self.started_at, 1),
            "goals": len(self.supervisor.list_goals()),
            "persist": self.config.persist,
            "briefing_enabled": self._briefing is not None,
        }

    # --------------------------------------------------------------- briefing

    async def _maybe_briefing(self) -> None:
        if self._briefing is None:
            return
        # Only trigger once per day (local date boundary).
        today = self._briefing.last_run_date
        if today == self._briefing.today():
            return
        objective = self._briefing.compose_objective()
        if objective is None:
            return
        logger.info("Running scheduled briefing")
        goal_id = await self.submit(objective, metadata={"kind": "briefing"})
        self._briefing.mark_run(goal_id)
        if self.config.persist:
            self._save()

    # ------------------------------------------------------------- persistence

    def _resolve_data_path(self) -> str:
        path = Path(self.config.data_dir).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return str(path / "daemon-state.json")

    def _load(self) -> None:
        try:
            with Path(self._data_path).open(encoding="utf-8") as fh:
                data = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return
        if self._briefing is not None:
            self._briefing.last_run_date = data.get("briefing_last_run", "")
        # Restore persisted goals so they survive a daemon restart (read-only).
        restored = data.get("goals") or []
        if restored:
            from .goal import Goal

            goals = [Goal.from_dict(g) for g in restored]
            self.supervisor.restore_goals(goals)
            logger.info("Restored %d goal(s) from %s", len(goals), self._data_path)

    def _save(self) -> None:
        data: dict[str, Any] = {
            "goals": self.supervisor.list_goals(),
            "briefing_last_run": (
                self._briefing.last_run_date if self._briefing else ""
            ),
        }
        try:
            with Path(self._data_path).open("w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, default=str)
        except OSError:
            logger.warning("Failed to persist daemon state", exc_info=True)


__all__ = ["Daemon", "DaemonConfig"]
