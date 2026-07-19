"""Tests for EventBus."""

import threading

from aios.agents.events import Event, EventBus, EventType, get_event_bus, reset_event_bus


class TestEventBus:
    def test_publish_subscribe(self):
        bus = EventBus()
        received = []
        bus.subscribe(EventType.SESSION_START, lambda e: received.append(e))
        event = bus.publish(EventType.SESSION_START, {"session_id": "123"})
        assert len(received) == 1
        assert received[0].event_type == EventType.SESSION_START
        assert received[0].data["session_id"] == "123"
        assert isinstance(event.timestamp, float)

    def test_publish_no_subscribers(self):
        bus = EventBus()
        event = bus.publish(EventType.SESSION_START)
        assert event.event_type == EventType.SESSION_START

    def test_multiple_subscribers(self):
        bus = EventBus()
        results = [0, 0]
        bus.subscribe(EventType.SESSION_START, lambda e: results.__setitem__(0, results[0] + 1))
        bus.subscribe(EventType.SESSION_START, lambda e: results.__setitem__(1, results[1] + 1))
        bus.publish(EventType.SESSION_START)
        assert results == [1, 1]

    def test_unsubscribe(self):
        bus = EventBus()
        received = []

        def handler(e):
            received.append(e)

        bus.subscribe(EventType.SESSION_START, handler)
        bus.unsubscribe(EventType.SESSION_START, handler)
        bus.publish(EventType.SESSION_START)
        assert len(received) == 0

    def test_unsubscribe_nonexistent(self):
        bus = EventBus()

        def handler(_e):
            return None

        # Should not raise
        bus.unsubscribe(EventType.SESSION_START, handler)

    def test_history_recording(self):
        bus = EventBus(record_history=True)
        bus.publish(EventType.SESSION_START)
        bus.publish(EventType.SESSION_END)
        assert len(bus.history) == 2
        assert bus.history[0].event_type == EventType.SESSION_START

    def test_history_disabled(self):
        bus = EventBus(record_history=False)
        bus.publish(EventType.SESSION_START)
        assert len(bus.history) == 0

    def test_clear_history(self):
        bus = EventBus(record_history=True)
        bus.publish(EventType.SESSION_START)
        bus.clear_history()
        assert len(bus.history) == 0

    def test_thread_safety(self):
        bus = EventBus(record_history=True)
        errors = []

        def publish_many(n):
            try:
                for _ in range(n):
                    bus.publish(EventType.SESSION_START)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=publish_many, args=(100,)) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert len(bus.history) == 1000


class TestEvent:
    def test_construction(self):
        event = Event(
            event_type=EventType.TOOL_CALL_START,
            timestamp=1000.0,
            data={"tool": "calc"},
        )
        assert event.event_type == EventType.TOOL_CALL_START
        assert event.data["tool"] == "calc"


class TestGetEventBus:
    def test_singleton(self):
        reset_event_bus()
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    def test_reset(self):
        reset_event_bus()
        bus1 = get_event_bus()
        reset_event_bus()
        bus2 = get_event_bus()
        assert bus1 is not bus2


class TestEventType:
    def test_all_event_types_are_strings(self):
        for et in EventType:
            assert isinstance(et, str)

    def test_event_type_count(self):
        assert len(EventType) == 17
