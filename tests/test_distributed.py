"""Tests for M3.4 — Distributed Execution.

Covers: queue, retry, dlq, persistence, priority, locking, worker,
scheduler, scaling, telemetry_hooks.
"""

from __future__ import annotations

import uuid

import pytest

from aios.distributed.dlq import DeadLetterEntry, DeadLetterQueue
from aios.distributed.persistence import TaskPersistence, TaskSnapshot, TaskState
from aios.distributed.priority import Priority, PriorityQueue
from aios.distributed.queue import InMemoryQueue, TaskMessage, TaskPriority
from aios.distributed.retry import ExponentialBackoff, RetryPolicy
from aios.distributed.scaling import LoadBalanceStrategy, PoolConfig, WorkerPool
from aios.distributed.scheduler import ScheduledJob, ScheduleType
from aios.distributed.telemetry_hooks import (
    LockMetrics,
    QueueMetrics,
    SchedulerMetrics,
    WorkerMetrics,
    traced_task,
)
from aios.distributed.worker import Worker, WorkerConfig
from aios.telemetry.metrics import MetricsCollector, MetricType


def _msg(queue: str = "default", task_type: str = "test") -> TaskMessage:
    return TaskMessage(
        id=str(uuid.uuid4().hex[:16]),
        queue=queue,
        payload={"type": task_type},
    )


# ── Queue ──────────────────────────────────────────────────────────────


class TestTaskMessage:
    def test_defaults(self):
        m = _msg()
        assert m.priority == TaskPriority.NORMAL
        assert m.attempt == 0
        assert m.queue == "default"
        assert len(m.id) == 16

    def test_json_roundtrip(self):
        m = _msg()
        raw = m.to_json()
        restored = TaskMessage.from_json(raw)
        assert restored.id == m.id
        assert restored.payload == m.payload
        assert restored.queue == m.queue

    def test_visible_by_default(self):
        m = _msg()
        assert m.is_visible() is True

    def test_ttl_zero_never_expires(self):
        m = _msg()
        m.ttl_seconds = 0
        assert m.is_expired() is False

    def test_ttl_positive_not_yet_expired(self):
        m = _msg()
        m.ttl_seconds = 9999
        assert m.is_expired() is False

    def test_json_preserves_priority(self):
        m = _msg()
        m.priority = TaskPriority.HIGH
        raw = m.to_json()
        restored = TaskMessage.from_json(raw)
        assert restored.priority == TaskPriority.HIGH


@pytest.fixture
def q():
    return InMemoryQueue()


class TestInMemoryQueue:
    @pytest.mark.anyio
    async def test_push_and_pop(self, q):
        m = _msg()
        await q.push(m)
        got = await q.pop("default")
        assert got is not None
        assert got.id == m.id

    @pytest.mark.anyio
    async def test_pop_empty(self, q):
        got = await q.pop("empty", timeout=0.05)
        assert got is None

    @pytest.mark.anyio
    async def test_ack_removes_from_processing(self, q):
        m = _msg()
        await q.push(m)
        got = await q.pop("default")
        assert got is not None
        await q.ack(got)
        proc = q._processing.get("default", [])
        assert got not in proc

    @pytest.mark.anyio
    async def test_nack_requeues(self, q):
        m = _msg()
        await q.push(m)
        got = await q.pop("default")
        assert got is not None
        await q.nack(got)
        assert await q.size("default") == 1

    @pytest.mark.anyio
    async def test_ack_idempotent(self, q):
        m = _msg()
        await q.ack(m)

    @pytest.mark.anyio
    async def test_size(self, q):
        assert await q.size() == 0
        await q.push(_msg())
        assert await q.size() == 1

    @pytest.mark.anyio
    async def test_purge(self, q):
        await q.push(_msg())
        await q.push(_msg())
        removed = await q.purge("default")
        assert removed == 2
        assert await q.size("default") == 0

    @pytest.mark.anyio
    async def test_peek(self, q):
        await q.push(_msg())
        await q.push(_msg())
        items = await q.peek("default", count=1)
        assert len(items) == 1


# ── Retry ──────────────────────────────────────────────────────────────


class TestExponentialBackoff:
    def test_base_delay_at_zero(self):
        b = ExponentialBackoff(base_delay=1.0, jitter=False)
        assert b.delay(0) == 1.0

    def test_increases(self):
        b = ExponentialBackoff(base_delay=0.5, max_delay=60.0, jitter=False)
        assert b.delay(0) < b.delay(1) < b.delay(2)

    def test_max_cap(self):
        b = ExponentialBackoff(base_delay=1.0, max_delay=5.0, jitter=False)
        assert b.delay(100) == 5.0

    def test_jitter_variance(self):
        b = ExponentialBackoff(base_delay=1.0, jitter=True, jitter_range=0.5)
        vals = [b.delay(0) for _ in range(50)]
        assert max(vals) - min(vals) > 0.01


class TestRetryPolicy:
    def test_should_retry_within_limit(self):
        p = RetryPolicy(max_retries=3)
        assert p.should_retry(RuntimeError("x"), 0) is True
        assert p.should_retry(RuntimeError("x"), 2) is True
        assert p.should_retry(RuntimeError("x"), 3) is False

    def test_non_retryable_by_default(self):
        p = RetryPolicy(max_retries=3)
        assert p.should_retry(ValueError("x"), 0) is False
        assert p.should_retry(TypeError("x"), 0) is False

    def test_retryable_whitelist_overrides_non_retryable(self):
        p = RetryPolicy(
            max_retries=5,
            non_retryable_exceptions=(RuntimeError,),
            retryable_exceptions=(ValueError,),
        )
        assert p.should_retry(ValueError("ok"), 0) is True
        assert p.should_retry(RuntimeError("bad"), 0) is False
        assert p.should_retry(TypeError("other"), 0) is False

    def test_time_until_retry(self):
        p = RetryPolicy(max_retries=5)
        assert p.time_until_retry(0) >= 0

    def test_fixed_strategy(self):
        p = RetryPolicy(strategy="fixed")
        assert p.delay_for_attempt(0) == p.delay_for_attempt(5)

    def test_linear_strategy(self):
        p = RetryPolicy(strategy="linear")
        assert p.delay_for_attempt(0) < p.delay_for_attempt(3)

    def test_immediate_strategy(self):
        p = RetryPolicy(strategy="immediate")
        assert p.delay_for_attempt(0) == 0.0

    def test_total_retry_time(self):
        p = RetryPolicy(max_retries=3)
        assert p.total_retry_time() > 0


# ── DLQ ────────────────────────────────────────────────────────────────


class TestDeadLetterQueue:
    @pytest.mark.anyio
    async def test_push_and_size(self):
        dlq = DeadLetterQueue(max_size=10)
        e = DeadLetterEntry(
            original_task=_msg(), error="boom", error_type="ValueError",
        )
        await dlq.push(e)
        assert dlq.size == 1

    @pytest.mark.anyio
    async def test_max_eviction(self):
        dlq = DeadLetterQueue(max_size=3)
        for i in range(5):
            await dlq.push(
                DeadLetterEntry(original_task=_msg(), error=f"e{i}", error_type="E"),
            )
        assert dlq.size == 3

    @pytest.mark.anyio
    async def test_purge_all(self):
        dlq = DeadLetterQueue()
        await dlq.push(DeadLetterEntry(original_task=_msg()))
        removed = await dlq.purge()
        assert removed == 1
        assert dlq.size == 0

    @pytest.mark.anyio
    async def test_query_by_error_type(self):
        dlq = DeadLetterQueue()
        await dlq.push(DeadLetterEntry(original_task=_msg(), error_type="ValueError"))
        await dlq.push(DeadLetterEntry(original_task=_msg(), error_type="TypeError"))
        results = dlq.query(error_type="ValueError")
        assert len(results) == 1

    @pytest.mark.anyio
    async def test_pop(self):
        dlq = DeadLetterQueue()
        e = DeadLetterEntry(original_task=_msg())
        await dlq.push(e)
        popped = await dlq.pop()
        assert popped is not None
        assert popped.id == e.id

    @pytest.mark.anyio
    async def test_pop_empty(self):
        dlq = DeadLetterQueue()
        assert await dlq.pop() is None

    def test_stats(self):
        dlq = DeadLetterQueue()
        stats = dlq.stats()
        assert stats["total"] == 0
        assert stats["max_size"] == 10_000


# ── Persistence ────────────────────────────────────────────────────────


@pytest.fixture
def persistence(tmp_path):
    return TaskPersistence(directory=tmp_path / "snapshots")


class TestTaskState:
    def test_transitions(self):
        s = TaskSnapshot(task=_msg(), state=TaskState.PENDING)
        s.transition(TaskState.PROCESSING)
        assert s.state == TaskState.PROCESSING
        assert len(s.history) == 1

    def test_terminal_not_blocked(self):
        s = TaskSnapshot(task=_msg(), state=TaskState.COMPLETED)
        s.transition(TaskState.PROCESSING)
        assert s.state == TaskState.PROCESSING


class TestTaskSnapshot:
    def test_roundtrip(self):
        snap = TaskSnapshot(
            task=_msg(),
            state=TaskState.PROCESSING,
            attempts=3,
            last_error="oops",
        )
        d = snap.to_dict()
        restored = TaskSnapshot.from_dict(d)
        assert restored.state == TaskState.PROCESSING
        assert restored.attempts == 3


class TestTaskPersistence:
    @pytest.mark.anyio
    async def test_initialize_creates_dir(self, persistence):
        await persistence.initialize()
        assert persistence.directory.exists()

    @pytest.mark.anyio
    async def test_save_and_load(self, persistence):
        await persistence.initialize()
        snap = TaskSnapshot(task=_msg(), state=TaskState.PENDING)
        await persistence.save(snap)
        loaded = await persistence.load(snap.task.id)
        assert loaded is not None
        assert loaded.state == TaskState.PENDING

    @pytest.mark.anyio
    async def test_list_tasks(self, persistence):
        await persistence.initialize()
        for _ in range(3):
            await persistence.save(TaskSnapshot(task=_msg(), state=TaskState.PENDING))
        await persistence.save(TaskSnapshot(task=_msg(), state=TaskState.COMPLETED))
        pending = await persistence.list_tasks(state=TaskState.PENDING)
        assert len(pending) == 3

    @pytest.mark.anyio
    async def test_delete(self, persistence):
        await persistence.initialize()
        snap = TaskSnapshot(task=_msg(), state=TaskState.PENDING)
        await persistence.save(snap)
        await persistence.delete(snap.task.id)
        loaded = await persistence.load(snap.task.id)
        assert loaded is None

    @pytest.mark.anyio
    async def test_count_by_state(self, persistence):
        await persistence.initialize()
        await persistence.save(TaskSnapshot(task=_msg(), state=TaskState.PENDING))
        await persistence.save(TaskSnapshot(task=_msg(), state=TaskState.COMPLETED))
        counts = await persistence.count_by_state()
        assert counts["pending"] == 1
        assert counts["completed"] == 1

    @pytest.mark.anyio
    async def test_recover_pending(self, persistence):
        await persistence.initialize()
        s1 = TaskSnapshot(task=_msg(), state=TaskState.PROCESSING)
        await persistence.save(s1)
        recovered = await persistence.recover_pending()
        assert len(recovered) == 1
        assert recovered[0].state == TaskState.RETRYING


# ── Priority ───────────────────────────────────────────────────────────


class TestPriorityQueue:
    @pytest.mark.anyio
    async def test_high_priority_first(self):
        pq = PriorityQueue()
        low = _msg()
        low.priority = Priority.LOW
        high = _msg()
        high.priority = Priority.HIGH
        await pq.push(low)
        await pq.push(high)
        got = await pq.pop(timeout=0.1)
        assert got is not None
        assert got.priority == Priority.HIGH

    @pytest.mark.anyio
    async def test_fifo_within_priority(self):
        pq = PriorityQueue()
        m1 = _msg()
        m1.priority = Priority.NORMAL
        m2 = _msg()
        m2.priority = Priority.NORMAL
        await pq.push(m1)
        await pq.push(m2)
        g1 = await pq.pop(timeout=0.1)
        g2 = await pq.pop(timeout=0.1)
        assert g1 is not None
        assert g2 is not None
        assert g1.id == m1.id
        assert g2.id == m2.id

    @pytest.mark.anyio
    async def test_empty_returns_none(self):
        pq = PriorityQueue()
        assert await pq.pop(timeout=0.05) is None

    def test_size(self):
        pq = PriorityQueue()
        assert pq.size() == 0

    def test_has_critical(self):
        pq = PriorityQueue()
        assert pq.has_critical() is False

    def test_highest_priority_none(self):
        pq = PriorityQueue()
        assert pq.highest_priority() is None


# ── Locking ────────────────────────────────────────────────────────────


class TestLockInfo:
    def test_creation(self):
        from aios.distributed.locking import LockInfo
        info = LockInfo(
            name="res", holder="h1",
            acquired_at=1.0, expires_at=2.0, ttl_seconds=30,
        )
        assert info.name == "res"
        assert info.ttl_seconds == 30


# ── Worker ─────────────────────────────────────────────────────────────


class TestWorker:
    @pytest.mark.anyio
    async def test_register_and_process(self):
        queue = InMemoryQueue()
        config = WorkerConfig(worker_id="w1")
        worker = Worker(queue=queue, config=config)

        handler_results = []

        async def handler(msg):
            handler_results.append(msg.id)
            return "ok"

        worker.register("test", handler)
        m = _msg()
        await worker._process_message(m)
        assert len(handler_results) == 1
        assert handler_results[0] == m.id
        assert worker.stats["tasks_processed"] == 1

    @pytest.mark.anyio
    async def test_no_handler_dlq(self):
        queue = InMemoryQueue()
        config = WorkerConfig(worker_id="w2")
        dlq = DeadLetterQueue()
        worker = Worker(queue=queue, config=config, dlq=dlq)
        m = _msg()
        await worker._process_message(m)
        assert dlq.size == 1

    @pytest.mark.anyio
    async def test_stats_property(self):
        queue = InMemoryQueue()
        config = WorkerConfig(worker_id="w3")
        worker = Worker(queue=queue, config=config)
        s = worker.stats
        assert isinstance(s, dict)
        assert s["worker_id"] == "w3"
        assert s["tasks_processed"] == 0

    @pytest.mark.anyio
    async def test_start_stop(self):
        queue = InMemoryQueue()
        worker = Worker(queue=queue)
        await worker.start()
        assert worker.is_running is True
        await worker.stop()
        assert worker.is_running is False


# ── Scheduler ──────────────────────────────────────────────────────────


class TestScheduledJob:
    def test_defaults(self):
        j = ScheduledJob(name="heartbeat")
        assert j.schedule_type == ScheduleType.INTERVAL
        assert j.schedule_expr == "60"
        assert j.enabled is True

    def test_fields(self):
        j = ScheduledJob(
            name="j",
            schedule_type=ScheduleType.ONCE,
            schedule_expr="2026-01-01T00:00:00",
            enabled=False,
            max_runs=10,
        )
        assert j.name == "j"
        assert j.max_runs == 10
        assert j.enabled is False


# ── Scaling ────────────────────────────────────────────────────────────


class TestScaling:
    def test_strategy_values(self):
        assert LoadBalanceStrategy.ROUND_ROBIN.value == "round_robin"
        assert LoadBalanceStrategy.LEAST_LOADED.value == "least_loaded"

    def test_pool_config_defaults(self):
        c = PoolConfig()
        assert c.size == 4
        assert c.strategy == LoadBalanceStrategy.ROUND_ROBIN

    @pytest.mark.anyio
    async def test_pool_status(self):
        queue = InMemoryQueue()
        pool = WorkerPool(queue=queue, config=PoolConfig(size=1))
        assert pool.size == 1
        assert pool.is_running is False


# ── Telemetry Hooks ────────────────────────────────────────────────────


class TestQueueMetrics:
    def test_enqueue(self):
        mc = MetricsCollector()
        qm = QueueMetrics(collector=mc)
        qm.record_enqueue("jobs", priority=1)
        assert mc.get_counter("aios.queue.enqueued", tags={"queue": "jobs", "priority": "1"}) == 1.0

    def test_dequeue(self):
        mc = MetricsCollector()
        qm = QueueMetrics(collector=mc)
        qm.record_dequeue("jobs")
        assert mc.get_counter("aios.queue.dequeued", tags={"queue": "jobs"}) == 1.0

    def test_ack_nack(self):
        mc = MetricsCollector()
        qm = QueueMetrics(collector=mc)
        qm.record_ack("q")
        qm.record_nack("q")
        assert mc.get_counter("aios.queue.acked", tags={"queue": "q"}) == 1.0
        assert mc.get_counter("aios.queue.nacked", tags={"queue": "q"}) == 1.0

    def test_depth(self):
        mc = MetricsCollector()
        qm = QueueMetrics(collector=mc)
        qm.record_depth("q", 42)
        assert mc.get_gauge("aios.queue.depth", tags={"queue": "q"}) == 42.0

    def test_error(self):
        mc = MetricsCollector()
        qm = QueueMetrics(collector=mc)
        qm.record_error("q", "TimeoutError")
        assert mc.get_counter(
            "aios.queue.errors", tags={"queue": "q", "error_type": "TimeoutError"},
        ) == 1.0

    def test_latency(self):
        mc = MetricsCollector()
        qm = QueueMetrics(collector=mc)
        qm.record_latency("q", "pop", 50.0)
        pts = mc.snapshot()
        lat = next((p for p in pts if p.name == "aios.queue.latency"), None)
        assert lat is not None
        assert lat.metric_type == MetricType.HISTOGRAM


class TestWorkerMetrics:
    def test_task_completed(self):
        mc = MetricsCollector()
        wm = WorkerMetrics(collector=mc)
        wm.record_task_completed("w1", "llm", 150.0)
        assert mc.get_counter(
            "aios.worker.completed", tags={"worker": "w1", "type": "llm"},
        ) == 1.0
        pts = mc.snapshot()
        dur = next((p for p in pts if p.name == "aios.worker.duration"), None)
        assert dur is not None
        assert dur.value == 150.0

    def test_task_failed(self):
        mc = MetricsCollector()
        wm = WorkerMetrics(collector=mc)
        wm.record_task_failed("w1", "llm", "TimeoutError")
        assert mc.get_counter(
            "aios.worker.failed",
            tags={"worker": "w1", "type": "llm", "error": "TimeoutError"},
        ) == 1.0

    def test_task_retried(self):
        mc = MetricsCollector()
        wm = WorkerMetrics(collector=mc)
        wm.record_task_retried("w1", 2)
        assert mc.get_counter(
            "aios.worker.retried", tags={"worker": "w1", "attempt": "2"},
        ) == 1.0

    def test_dlq(self):
        mc = MetricsCollector()
        wm = WorkerMetrics(collector=mc)
        wm.record_dlq("w1", "llm")
        assert mc.get_counter(
            "aios.worker.dead_lettered", tags={"worker": "w1", "type": "llm"},
        ) == 1.0

    def test_active_workers(self):
        mc = MetricsCollector()
        wm = WorkerMetrics(collector=mc)
        wm.record_active_workers(5)
        assert mc.get_gauge("aios.worker.active") == 5.0


class TestSchedulerMetrics:
    def test_job_fired(self):
        mc = MetricsCollector()
        sm = SchedulerMetrics(collector=mc)
        sm.record_job_fired("cleanup")
        assert mc.get_counter("aios.scheduler.fired", tags={"job": "cleanup"}) == 1.0

    def test_job_error(self):
        mc = MetricsCollector()
        sm = SchedulerMetrics(collector=mc)
        sm.record_job_error("cleanup", "RuntimeError")
        assert mc.get_counter(
            "aios.scheduler.errors", tags={"job": "cleanup", "error": "RuntimeError"},
        ) == 1.0

    def test_scheduled_jobs_gauge(self):
        mc = MetricsCollector()
        sm = SchedulerMetrics(collector=mc)
        sm.record_scheduled_jobs(10)
        assert mc.get_gauge("aios.scheduler.jobs") == 10.0


class TestLockMetrics:
    def test_acquire(self):
        mc = MetricsCollector()
        lm = LockMetrics(collector=mc)
        lm.record_acquire("my-lock", success=True)
        assert mc.get_counter(
            "aios.lock.acquire", tags={"lock": "my-lock", "success": "true"},
        ) == 1.0

    def test_release(self):
        mc = MetricsCollector()
        lm = LockMetrics(collector=mc)
        lm.record_release("my-lock")
        assert mc.get_counter("aios.lock.released", tags={"lock": "my-lock"}) == 1.0

    def test_contention(self):
        mc = MetricsCollector()
        lm = LockMetrics(collector=mc)
        lm.record_contention("my-lock", 50.0)
        pts = mc.snapshot()
        c = next((p for p in pts if p.name == "aios.lock.contention"), None)
        assert c is not None
        assert c.value == 50.0


class TestTracedTask:
    @pytest.mark.anyio
    async def test_runs_handler(self):
        @traced_task("test.handler")
        async def my_handler(msg):
            return msg

        result = await my_handler("hello")
        assert result == "hello"

    def test_returns_callable(self):
        @traced_task("test.x")
        async def fn():
            pass

        assert callable(fn)
