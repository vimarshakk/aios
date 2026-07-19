"""Horizontal scaling — worker pool management and load balancing.

Provides a WorkerPool that spawns multiple Worker instances across
processes or threads, with round-robin and least-loaded dispatch.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from aios.distributed.worker import Handler, Worker, WorkerConfig

if TYPE_CHECKING:
    from aios.distributed.queue import QueueBackend


class LoadBalanceStrategy(StrEnum):
    """Strategy for distributing tasks across workers."""

    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"


@dataclass
class PoolConfig:
    """Configuration for a worker pool.

    Attributes:
        size: Number of worker instances to manage.
        strategy: Load balancing strategy.
        queue_names: Queues all workers consume from.
        handler_timeout: Max seconds per task handler execution.
    """

    size: int = 4
    strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN
    queue_names: list[str] = field(default_factory=lambda: ["default"])
    handler_timeout: float = 300.0


class WorkerPool:
    """Manages a pool of in-process Worker instances.

    All workers share the same queue backend but run as independent
    asyncio tasks, providing concurrency for task processing.

    Usage::

        pool = WorkerPool(queue=queue_backend, config=PoolConfig(size=4))
        pool.register("llm.generate", my_handler)
        await pool.start()
        # ... later ...
        await pool.stop()
    """

    def __init__(
        self,
        queue: QueueBackend,
        config: PoolConfig | None = None,
    ) -> None:
        self._queue = queue
        self._config = config or PoolConfig()
        self._workers: list[Worker] = []
        self._tasks: list[asyncio.Task[None]] = []
        self._running = False
        self._round_robin_index = 0
        self._handlers: dict[str, Handler] = {}

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def size(self) -> int:
        return self._config.size

    def register(self, task_type: str, handler: Handler) -> None:
        """Register a handler for all workers in the pool."""
        self._handlers[task_type] = handler
        for worker in self._workers:
            worker.register(task_type, handler)

    def unregister(self, task_type: str) -> None:
        """Remove a handler from all workers."""
        self._handlers.pop(task_type, None)
        for worker in self._workers:
            worker.unregister(task_type)

    async def start(self) -> None:
        """Start all workers in the pool."""
        if self._running:
            return
        self._running = True
        for i in range(self._config.size):
            config = WorkerConfig(
                worker_id=f"pool-worker-{i}",
                queue_names=list(self._config.queue_names),
                handler_timeout=self._config.handler_timeout,
            )
            worker = Worker(queue=self._queue, config=config)
            for task_type, handler in self._handlers.items():
                worker.register(task_type, handler)
            self._workers.append(worker)
            await worker.start()
            task = asyncio.create_task(worker.run_forever(), name=f"pool-{i}")
            self._tasks.append(task)

    async def stop(self) -> None:
        """Stop all workers in the pool."""
        self._running = False
        for worker in self._workers:
            await worker.stop()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._workers.clear()

    async def scale(self, new_size: int) -> None:
        """Dynamically resize the worker pool.

        Args:
            new_size: New number of workers.
        """
        if new_size == self._config.size:
            return
        if new_size > self._config.size:
            for i in range(self._config.size, new_size):
                config = WorkerConfig(
                    worker_id=f"pool-worker-{i}",
                    queue_names=list(self._config.queue_names),
                    handler_timeout=self._config.handler_timeout,
                )
                worker = Worker(queue=self._queue, config=config)
                for task_type, handler in self._handlers.items():
                    worker.register(task_type, handler)
                self._workers.append(worker)
                await worker.start()
                task = asyncio.create_task(worker.run_forever(), name=f"pool-{i}")
                self._tasks.append(task)
        else:
            for i in range(new_size, self._config.size):
                if i < len(self._workers):
                    await self._workers[i].stop()
                    if i < len(self._tasks):
                        self._tasks[i].cancel()
            self._workers = self._workers[:new_size]
            self._tasks = self._tasks[:new_size]
        self._config.size = new_size

    def get_worker(self) -> Worker | None:
        """Get a worker using the configured load-balance strategy."""
        if not self._workers:
            return None
        if self._config.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            worker = self._workers[self._round_robin_index % len(self._workers)]
            self._round_robin_index += 1
            return worker
        if self._config.strategy == LoadBalanceStrategy.LEAST_LOADED:
            return min(self._workers, key=lambda w: w.stats.get("current_tasks", 0))
        return self._workers[0]

    def stats(self) -> list[dict[str, Any]]:
        """Get stats for all workers in the pool."""
        return [w.stats for w in self._workers]

    async def health_check(self) -> dict[str, Any]:
        """Pool health status."""
        worker_checks = await asyncio.gather(
            *[w.health_check() for w in self._workers],
            return_exceptions=True,
        )
        healthy_count = sum(
            1 for r in worker_checks
            if isinstance(r, dict) and r.get("healthy", False)
        )
        return {
            "running": self._running,
            "pool_size": self._config.size,
            "healthy_workers": healthy_count,
            "strategy": self._config.strategy.value,
        }


class Autoscaler:
    """Dynamic autoscaler that adjusts pool size based on queue depth.

    Monitors the queue and scales workers up/down based on
    configurable thresholds.

    Usage::

        autoscaler = Autoscaler(pool=worker_pool, queue=queue_backend)
        await autoscaler.start()
        # ... runs monitoring loop in background ...
        await autoscaler.stop()
    """

    def __init__(
        self,
        pool: WorkerPool,
        queue: QueueBackend,
        queue_name: str = "default",
        min_workers: int = 1,
        max_workers: int = 16,
        scale_up_threshold: int = 10,
        scale_down_threshold: int = 2,
        check_interval: float = 5.0,
    ) -> None:
        self._pool = pool
        self._queue = queue
        self._queue_name = queue_name
        self._min = min_workers
        self._max = max_workers
        self._up_threshold = scale_up_threshold
        self._down_threshold = scale_down_threshold
        self._check_interval = check_interval
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._scale_events: list[dict[str, Any]] = []

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def scale_events(self) -> list[dict[str, Any]]:
        return list(self._scale_events)

    async def start(self) -> None:
        """Start the autoscaler monitoring loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop the autoscaler."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            depth = await self._queue.size(self._queue_name)
            current = self._pool.size
            new_size = current
            if depth > self._up_threshold and current < self._max:
                new_size = min(current + max(1, depth // self._up_threshold), self._max)
            elif depth < self._down_threshold and current > self._min:
                new_size = max(current - 1, self._min)
            if new_size != current:
                event = {
                    "action": "scale_up" if new_size > current else "scale_down",
                    "from": current,
                    "to": new_size,
                    "queue_depth": depth,
                }
                self._scale_events.append(event)
                await self._pool.scale(new_size)
            await asyncio.sleep(self._check_interval)


__all__ = [
    "Autoscaler",
    "LoadBalanceStrategy",
    "PoolConfig",
    "WorkerPool",
]
