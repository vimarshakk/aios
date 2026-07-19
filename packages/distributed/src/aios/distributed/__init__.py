"""AIOS Distributed Execution.

Redis-backed task queue, workers, retry, DLQ, persistence, locking, scaling.
"""

from __future__ import annotations

from aios.distributed.dlq import DeadLetterEntry, DeadLetterQueue
from aios.distributed.locking import DistributedLock, LockManager
from aios.distributed.persistence import TaskPersistence, TaskSnapshot
from aios.distributed.priority import Priority, PriorityQueue
from aios.distributed.queue import InMemoryQueue, QueueBackend, RedisQueue, TaskMessage
from aios.distributed.retry import ExponentialBackoff, RetryExhaustedError, RetryPolicy
from aios.distributed.worker import Worker, WorkerConfig

API_VERSION = "1.0"

__all__ = [
    "API_VERSION",
    "DeadLetterEntry",
    "DeadLetterQueue",
    "DistributedLock",
    "ExponentialBackoff",
    "InMemoryQueue",
    "LockManager",
    "Priority",
    "PriorityQueue",
    "QueueBackend",
    "RedisQueue",
    "RetryExhaustedError",
    "RetryPolicy",
    "TaskMessage",
    "TaskPersistence",
    "TaskSnapshot",
    "Worker",
    "WorkerConfig",
]
