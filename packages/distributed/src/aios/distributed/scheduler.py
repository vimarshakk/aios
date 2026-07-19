"""Scheduler integration — delayed, recurring, and cron-based task scheduling.

Wraps APScheduler to provide AIOS-native scheduling with queue integration,
supporting one-shot delayed tasks, recurring intervals, and cron expressions.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from aios.distributed.queue import QueueBackend, TaskMessage, TaskPriority


class ScheduleType(StrEnum):
    """Schedule type identifiers."""

    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"


@dataclass
class ScheduledJob:
    """A scheduled job definition.

    Attributes:
        id: Unique job identifier.
        name: Human-readable job name.
        schedule_type: Type of schedule (once, interval, cron).
        schedule_expr: Schedule expression (ISO datetime, seconds, or cron string).
        queue_name: Target queue name.
        payload: Task payload to enqueue when the job fires.
        priority: Task priority for the enqueued task.
        enabled: Whether the job is active.
        max_runs: Maximum number of times to fire; None for unlimited.
        run_count: Number of times the job has fired.
        last_run_at: Timestamp of the last fire.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    schedule_type: ScheduleType = ScheduleType.INTERVAL
    schedule_expr: str = "60"
    queue_name: str = "default"
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = TaskPriority.NORMAL
    enabled: bool = True
    max_runs: int | None = None
    run_count: int = 0
    last_run_at: float = 0.0


class Scheduler:
    """AIOS task scheduler with queue integration.

    Wraps APScheduler to provide AIOS-native scheduling. Jobs enqueue
    TaskMessages into the specified queue backend when they fire.

    Usage::

        scheduler = Scheduler(queue=queue_backend)
        scheduler.start()
        job = ScheduledJob(
            name="heartbeat",
            schedule_type=ScheduleType.INTERVAL,
            schedule_expr="30",
            payload={"type": "health_check"},
        )
        scheduler.add_job(job)
        # ...
        scheduler.stop()
    """

    def __init__(self, queue: QueueBackend) -> None:
        self._queue = queue
        self._apscheduler = AsyncIOScheduler()
        self._jobs: dict[str, ScheduledJob] = {}
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the scheduler."""
        if not self._running:
            self._apscheduler.start()
            self._running = True

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._running:
            self._apscheduler.shutdown(wait=False)
            self._running = False

    def add_job(self, job: ScheduledJob) -> str:
        """Register and schedule a job.

        Args:
            job: The job definition.

        Returns:
            The job ID.
        """
        self._jobs[job.id] = job
        trigger = self._build_trigger(job)
        self._apscheduler.add_job(
            self._fire_job,
            trigger=trigger,
            id=job.id,
            name=job.name or job.id,
            args=[job],
            replace_existing=True,
        )
        return job.id

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job.

        Returns:
            True if the job was found and removed.
        """
        self._jobs.pop(job_id, None)
        try:
            self._apscheduler.remove_job(job_id)
            return True
        except Exception:
            return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job."""
        try:
            self._apscheduler.pause_job(job_id)
            if job_id in self._jobs:
                self._jobs[job_id].enabled = False
            return True
        except Exception:
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        try:
            self._apscheduler.resume_job(job_id)
            if job_id in self._jobs:
                self._jobs[job_id].enabled = True
            return True
        except Exception:
            return False

    def get_job(self, job_id: str) -> ScheduledJob | None:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[ScheduledJob]:
        return list(self._jobs.values())

    async def _fire_job(self, job: ScheduledJob) -> None:
        """Callback when a scheduled job fires — enqueue a task message."""
        if job.max_runs is not None and job.run_count >= job.max_runs:
            self.remove_job(job.id)
            return
        msg = TaskMessage(
            queue=job.queue_name,
            payload=job.payload.copy(),
            priority=job.priority,
            metadata={"scheduled_job_id": job.id, "scheduled_job_name": job.name},
        )
        await self._queue.push(msg)
        job.run_count += 1
        job.last_run_at = time.time()

    def _build_trigger(self, job: ScheduledJob) -> Any:
        """Build an APScheduler trigger from a ScheduledJob."""
        if job.schedule_type == ScheduleType.INTERVAL:
            seconds = int(job.schedule_expr)
            return IntervalTrigger(seconds=seconds)
        if job.schedule_type == ScheduleType.CRON:
            parts = job.schedule_expr.split()
            minute, hour, day, month, dow = ([*parts, "*", "*", "*", "*", "*"])[:5]
            return CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=dow)
        if job.schedule_type == ScheduleType.ONCE:
            run_at = datetime.fromisoformat(job.schedule_expr)
            return DateTrigger(run_date=run_at)
        return IntervalTrigger(seconds=60)

    async def health_check(self) -> dict[str, Any]:
        """Scheduler health status."""
        return {
            "running": self._running,
            "total_jobs": len(self._jobs),
            "enabled_jobs": sum(1 for j in self._jobs.values() if j.enabled),
        }


__all__ = [
    "ScheduleType",
    "ScheduledJob",
    "Scheduler",
]
