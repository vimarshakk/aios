"""Thread-safe pub/sub event bus for inter-primitive communication.

Extracted from OpenJarvis core/events.py (Apache 2.0).
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    INFERENCE_START = "inference_start"
    INFERENCE_END = "inference_end"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    MEMORY_STORE = "memory_store"
    MEMORY_RETRIEVE = "memory_retrieve"
    CHAT_EXCHANGE_COMPLETED = "chat_exchange_completed"
    AGENT_TURN_START = "agent_turn_start"
    AGENT_TURN_END = "agent_turn_end"
    TELEMETRY_RECORD = "telemetry_record"
    TRACE_STEP = "trace_step"
    TRACE_COMPLETE = "trace_complete"
    TOOL_TIMEOUT = "tool_timeout"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_END = "workflow_end"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


@dataclass(slots=True)
class Event:
    event_type: EventType
    timestamp: float
    data: dict[str, Any] = field(default_factory=dict)


Subscriber = Callable[[Event], None]


class EventBus:
    """Thread-safe publish/subscribe event bus."""

    def __init__(self, *, record_history: bool = False) -> None:
        self._subscribers: dict[EventType, list[Subscriber]] = {}
        self._lock = threading.Lock()
        self._record_history = record_history
        self._history: list[Event] = []

    def subscribe(self, event_type: EventType, callback: Subscriber) -> None:
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type: EventType, callback: Subscriber) -> None:
        with self._lock:
            listeners = self._subscribers.get(event_type, [])
            with contextlib.suppress(ValueError):
                listeners.remove(callback)

    def publish(
        self,
        event_type: EventType,
        data: dict[str, Any] | None = None,
    ) -> Event:
        event = Event(event_type=event_type, timestamp=time.time(), data=data or {})
        with self._lock:
            if self._record_history:
                self._history.append(event)
            listeners = list(self._subscribers.get(event_type, []))
        for callback in listeners:
            callback(event)
        return event

    @property
    def history(self) -> list[Event]:
        with self._lock:
            return list(self._history)

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()


_bus: EventBus | None = None
_bus_lock = threading.Lock()


def get_event_bus(*, record_history: bool = False) -> EventBus:
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = EventBus(record_history=record_history)
        return _bus


def reset_event_bus() -> None:
    global _bus
    with _bus_lock:
        _bus = None


__all__ = [
    "Event",
    "EventBus",
    "EventType",
    "Subscriber",
    "get_event_bus",
    "reset_event_bus",
]
