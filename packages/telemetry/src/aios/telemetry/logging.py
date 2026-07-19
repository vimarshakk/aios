"""Structured logging — JSON-formatted logging with context propagation.

Uses structlog for structured, machine-parseable log output with
correlation IDs, subsystem tags, and level filtering.
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")
_subsystem: ContextVar[str] = ContextVar("subsystem", default="core")


def setup_logging(
    level: str = "INFO",
    *,
    json_output: bool = True,
    correlate: bool = True,
) -> None:
    """Configure structlog with processors for structured logging.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_output: If True, render as JSON. If False, render as colored console.
        correlate: If True, auto-inject correlation_id into all log entries.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if correlate:
        shared_processors.append(_add_correlation_id)

    shared_processors.append(_add_subsystem)

    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)  # noqa: F841

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(message)s")
        if json_output
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_logger(name: str = "aios") -> structlog.stdlib.BoundLogger:
    """Get a named structlog logger.

    Args:
        name: Logger name (typically subsystem name).

    Returns:
        A bound logger with the given name.
    """
    return structlog.get_logger(name)


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set the current correlation ID for request tracing.

    If no ID is provided, a new UUID is generated.

    Returns:
        The correlation ID that was set.
    """
    cid = correlation_id or uuid.uuid4().hex[:12]
    _correlation_id.set(cid)
    return cid


def get_correlation_id() -> str:
    """Get the current correlation ID."""
    return _correlation_id.get()


def set_subsystem(name: str) -> None:
    """Set the current subsystem name for log entries."""
    _subsystem.set(name)


def get_subsystem() -> str:
    """Get the current subsystem name."""
    return _subsystem.get()


def _add_correlation_id(
    logger: Any, method_name: str, event_dict: dict[str, Any],  # noqa: ARG001
) -> dict[str, Any]:
    """Add correlation_id to log entries."""
    cid = _correlation_id.get()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def _add_subsystem(
    logger: Any, method_name: str, event_dict: dict[str, Any],  # noqa: ARG001
) -> dict[str, Any]:
    """Add subsystem to log entries."""
    sub = _subsystem.get()
    if sub:
        event_dict["subsystem"] = sub
    return event_dict


__all__ = [
    "get_correlation_id",
    "get_logger",
    "get_subsystem",
    "set_correlation_id",
    "set_subsystem",
    "setup_logging",
]
