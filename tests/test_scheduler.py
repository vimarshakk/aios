"""Tests for TaskScheduler."""


from aios.scheduler.task_scheduler import ScheduledTask, TaskScheduler


async def dummy_handler():
    pass


class TestScheduledTask:
    def test_construction(self):
        task = ScheduledTask(
            id="t1",
            name="Test Task",
            handler=dummy_handler,
            schedule="interval: 60",
        )
        assert task.id == "t1"
        assert task.enabled is True

    def test_defaults(self):
        task = ScheduledTask(
            id="t1",
            name="Test",
            handler=dummy_handler,
            schedule="once: 2025-12-31T00:00:00",
        )
        assert task.args == ()
        assert task.kwargs == {}


class TestTaskScheduler:
    def test_construction(self):
        sched = TaskScheduler()
        assert sched.list_tasks() == []

    def test_add_task(self):
        sched = TaskScheduler()
        task = ScheduledTask(
            id="t1",
            name="Test",
            handler=dummy_handler,
            schedule="interval: 60",
        )
        sched.add_task(task)
        assert len(sched.list_tasks()) == 1

    def test_remove_task(self):
        sched = TaskScheduler()
        task = ScheduledTask(
            id="t1",
            name="Test",
            handler=dummy_handler,
            schedule="interval: 60",
        )
        sched.add_task(task)
        sched.remove_task("t1")
        assert len(sched.list_tasks()) == 0

    def test_remove_nonexistent_task(self):
        sched = TaskScheduler()
        # Should not raise
        sched.remove_task("nonexistent")

    def test_parse_trigger_interval(self):
        sched = TaskScheduler()
        trigger = sched._parse_trigger("interval: 30")
        assert trigger is not None

    def test_parse_trigger_cron(self):
        sched = TaskScheduler()
        trigger = sched._parse_trigger("cron: */5 * * * *")
        assert trigger is not None

    def test_parse_trigger_once(self):
        sched = TaskScheduler()
        trigger = sched._parse_trigger("once: 2025-12-31T00:00:00")
        assert trigger is not None

    def test_parse_trigger_unknown(self):
        sched = TaskScheduler()
        trigger = sched._parse_trigger("unknown format")
        assert trigger is not None  # defaults to 60s interval
