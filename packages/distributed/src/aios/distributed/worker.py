"""Worker execution framework — pulls tasks from queues and executes them.

Provides a Worker that consumes TaskMessages from a QueueBackend,
executes registered handlers with retry support, and emits telemetry events.
"""

from __future__ import annotations

import asyncio
import time
import traceback
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from aios.distributed.dlq import DeadLetterEntry, DeadLetterQueue
from aios.distributed.persistence import TaskPersistence, TaskSnapshot, TaskState
from aios.distributed.queue import QueueBackend, TaskMessage
from aios.distributed.retry import RetryPolicy


@dataclass
class WorkerConfig:
    """Configuration for a worker instance.

    Attributes:
        worker_id: Unique identifier for this worker.
        queue_names: List of queue names to consume from.
        poll_interval: Seconds between polls when the queue is empty.
        batch_size: Max tasks to process per poll cycle.
        handler_timeout: Max seconds for a single handler execution.
        enable_persistence: Whether to persist task state.
        enable_dlq: Whether to dead-letter permanently failed tasks.
    """

    worker_id: str = ""
    queue_names: list[str] = field(default_factory=lambda: ["default"])
    poll_interval: float = 0.1
    batch_size: int = 1
    handler_timeout: float = 300.0
    enable_persistence: bool = False
    enable_dlq: bool = True

    def __post_init__(self) -> None:
        if not self.worker_id:
            import uuid as _uuid
            self.worker_id = f"worker-{_uuid.uuid4().hex[:8]}"


Handler = Callable[[TaskMessage], Coroutine[Any, Any, Any]]


class Worker:
    """Task execution worker with retry, DLQ, and persistence support.

    Usage::

        worker = Worker(queue=queue_backend, config=WorkerConfig())
        worker.register("llm.generate", my_handler)
        await worker.start()
        # ... later ...
        await worker.stop()
    """

    def __init__(
        self,
        queue: QueueBackend,
        config: WorkerConfig | None = None,
        retry_policy: RetryPolicy | None = None,
        dlq: DeadLetterQueue | None = None,
        persistence: TaskPersistence | None = None,
    ) -> None:
        self._queue = queue
        self._config = config or WorkerConfig()
        self._retry = retry_policy or RetryPolicy()
        self._dlq = dlq
        self._persistence = persistence
        self._handlers: dict[str, Handler] = {}
        self._running = False
        self._tasks_processed = 0
        self._tasks_failed = 0
        self._tasks_dlq = 0
        self._start_time: float | None = None
        self._current_tasks: dict[str, asyncio.Task[Any]] = {}

    @property
    def worker_id(self) -> str:
        return self._config.worker_id

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "worker_id": self._config.worker_id,
            "running": self._running,
            "tasks_processed": self._tasks_processed,
            "tasks_failed": self._tasks_failed,
            "tasks_dead_lettered": self._tasks_dlq,
            "uptime_seconds": round(time.time() - self._start_time, 1) if self._start_time else 0,
            "current_tasks": len(self._current_tasks),
        }

    def register(self, task_type: str, handler: Handler) -> None:
        """Register a handler for a task type.

        The task type is determined by ``payload.get("type", task_type)``.

        Args:
            task_type: The task type string this handler handles.
            handler: Async callable that processes the task.
        """
        self._handlers[task_type] = handler

    def unregister(self, task_type: str) -> None:
        """Remove a handler for a task type."""
        self._handlers.pop(task_type, None)

    async def start(self) -> None:
        """Start the worker event loop."""
        self._running = True
        self._start_time = time.time()
        if self._persistence:
            await self._persistence.initialize()

    async def stop(self) -> None:
        """Stop the worker and wait for in-flight tasks."""
        self._running = False
        if self._current_tasks:
            await asyncio.gather(*self._current_tasks.values(), return_exceptions=True)
        self._current_tasks.clear()

    async def run_once(self) -> int:
        """Process one batch of tasks.

        Returns:
            Number of tasks processed in this cycle.
        """
        processed = 0
        for queue_name in self._config.queue_names:
            for _ in range(self._config.batch_size):
                msg = await self._queue.pop(queue=queue_name, timeout=0.05)
                if msg is None:
                    break
                await self._process_message(msg)
                processed += 1
        return processed

    async def run_forever(self) -> None:
        """Run the worker in a continuous loop until stopped."""
        while self._running:
            count = await self.run_once()
            if count == 0:
                await asyncio.sleep(self._config.poll_interval)

    async def _process_message(self, message: TaskMessage) -> None:
        """Process a single task message with retry and error handling."""
        task_type = message.payload.get("type", "default")
        handler = self._handlers.get(task_type)

        if handler is None:
            self._tasks_failed += 1
            msg = f"No handler for task type '{task_type}'"
            await self._maybe_dead_letter(message, Exception(msg))
            return

        snapshot = None
        if self._persistence:
            snapshot = TaskSnapshot(task=message, state=TaskState.PROCESSING)
            snapshot.attempts = message.attempt
            await self._persistence.save(snapshot)

        task_key = message.id
        task = asyncio.create_task(
            self._execute_with_retry(message, handler, snapshot),
            name=f"task-{task_key}",
        )
        self._current_tasks[task_key] = task
        try:
            await task
        finally:
            self._current_tasks.pop(task_key, None)

    async def _execute_with_retry(
        self,
        message: TaskMessage,
        handler: Handler,
        snapshot: TaskSnapshot | None,
    ) -> None:
        """Execute a handler with retry logic."""
        last_error: Exception | None = None
        for attempt in range(self._retry.max_retries + 1):
            message.attempt = attempt
            try:
                if snapshot:
                    snapshot.attempts = attempt
                result = await asyncio.wait_for(
                    handler(message),
                    timeout=self._config.handler_timeout,
                )
                await self._queue.ack(message)
                self._tasks_processed += 1
                if snapshot:
                    snapshot.transition(TaskState.COMPLETED)
                    snapshot.result = result
                    await self._persistence.save(snapshot)  # type: ignore[union-attr]
                return
            except Exception as exc:
                last_error = exc
                if not self._retry.should_retry(exc, attempt):
                    break
                delay = self._retry.time_until_retry(attempt)
                if snapshot:
                    snapshot.transition(
                        TaskState.RETRYING,
                        error=str(exc),
                        error_type=type(exc).__name__,
                    )
                    await self._persistence.save(snapshot)  # type: ignore[union-attr]
                if delay > 0:
                    await asyncio.sleep(delay)

        self._tasks_failed += 1
        await self._queue.nack(message)
        await self._maybe_dead_letter(message, last_error)  # type: ignore[arg-type]
        if snapshot:
            snapshot.transition(
                TaskState.FAILED,
                error=str(last_error),
                error_type=type(last_error).__name__,  # type: ignore[arg-type]
            )
            await self._persistence.save(snapshot)  # type: ignore[union-attr]

    async def _maybe_dead_letter(self, message: TaskMessage, error: Exception) -> None:
        """Send a task to the DLQ if enabled."""
        if not self._dlq or not self._config.enable_dlq:
            return
        entry = DeadLetterEntry(
            original_task=message,
            error=str(error),
            error_type=type(error).__name__,
            total_attempts=message.attempt + 1,
            source_queue=message.queue,
            stacktrace=traceback.format_exc(),
        )
        await self._dlq.push(entry)
        self._tasks_dlq += 1

    async def health_check(self) -> dict[str, Any]:
        """Return worker health status."""
        return {
            "worker_id": self.worker_id,
            "healthy": self._running,
            **self.stats,
        }


__all__ = [
    "Handler",
    "Worker",
    "WorkerConfig",
]
