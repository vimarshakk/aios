"""Task scheduler for recurring and one-shot agent tasks.

Extracted from OpenJarvis scheduler patterns (Apache 2.0).
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine


@dataclass
class ScheduledTask:
    id: str
    name: str
    handler: Callable[..., Coroutine[Any, Any, Any]]
    schedule: str  # "cron: * * * * *", "interval: 60", "once: 2025-01-01T00:00:00"
    args: tuple = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class TaskScheduler:
    """Schedule recurring and one-shot tasks with agent integration."""

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._tasks: dict[str, ScheduledTask] = {}

    def start(self) -> None:
        self._scheduler.start()

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)

    def add_task(self, task: ScheduledTask) -> None:
        """Register and schedule a task."""
        self._tasks[task.id] = task
        trigger = self._parse_trigger(task.schedule)
        self._scheduler.add_job(
            task.handler,
            trigger=trigger,
            id=task.id,
            name=task.name,
            args=task.args,
            kwargs=task.kwargs,
            replace_existing=True,
        )

    def remove_task(self, task_id: str) -> None:
        if task_id in self._tasks:
            del self._tasks[task_id]
        with contextlib.suppress(Exception):
            self._scheduler.remove_job(task_id)

    def list_tasks(self) -> list[ScheduledTask]:
        return list(self._tasks.values())

    def _parse_trigger(self, schedule: str) -> Any:
        if schedule.startswith("cron:"):
            parts = schedule[5:].strip().split()
            minute, hour, day, month, dow = ([*parts, "*", "*", "*", "*", "*"])[:5]
            return CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=dow)
        if schedule.startswith("interval:"):
            seconds = int(schedule[9:].strip())
            return IntervalTrigger(seconds=seconds)
        if schedule.startswith("once:"):
            run_at = datetime.fromisoformat(schedule[5:].strip())
            return DateTrigger(run_date=run_at)
        return IntervalTrigger(seconds=60)


__all__ = ["ScheduledTask", "TaskScheduler"]
