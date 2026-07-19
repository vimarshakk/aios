"""OpenTelemetry tracing — distributed tracing for AIOS subsystems.

Provides a singleton TracerProvider, named tracers for each subsystem,
and a convenience decorator for tracing arbitrary async functions.
"""

from __future__ import annotations

import contextlib
import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider as SdkTracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

F = TypeVar("F", bound=Callable[..., Any])

_provider: trace.TracerProvider | None = None


def init_tracing(
    service_name: str = "aios",
    *, console_export: bool = False, endpoint: str | None = None,
) -> trace.TracerProvider:
    """Initialize the global OpenTelemetry TracerProvider.

    This should be called once at application startup. Subsequent calls
    are no-ops unless ``reset_tracing()`` is called first.

    Args:
        service_name: The service name for resource attribution.
        console_export: If True, export spans to stdout (development).
        endpoint: OTLP collector endpoint. If provided, enables OTLP export.

    Returns:
        The initialized TracerProvider.
    """
    global _provider
    if _provider is not None:
        return _provider

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = SdkTracerProvider(resource=resource)

    if console_export or endpoint is None:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    if endpoint:
        with contextlib.suppress(ImportError):
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(SimpleSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    _provider = provider
    return provider


def reset_tracing() -> None:
    """Reset the global tracer provider (for testing)."""
    global _provider
    if _provider is not None:
        with contextlib.suppress(Exception):
            _provider.shutdown()
    _provider = None


def get_tracer(name: str = "aios") -> trace.Tracer:
    """Get a named tracer from the global provider.

    If the provider hasn't been initialized, a no-op tracer is returned.
    """
    return trace.get_tracer(name)


def trace_operation(
    name: str,
    *,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None,
) -> Callable[[F], F]:
    """Decorator that wraps an async function in an OpenTelemetry span.

    Usage::

        @trace_operation("llm.complete", kind=SpanKind.CLIENT)
        async def complete(prompt: str) -> str:
            ...
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer("aios.tracing")
            with tracer.start_as_current_span(
                name,
                kind=kind,
                attributes=attributes or {},
            ) as span:
                start = time.monotonic()
                try:
                    result = await fn(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    span.record_exception(exc)
                    raise
                finally:
                    span.set_attribute("duration_ms", (time.monotonic() - start) * 1000)

        return wrapper  # type: ignore[return-value]

    return decorator


def trace_sync(
    name: str,
    *,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None,
) -> Callable[[F], F]:
    """Decorator that wraps a synchronous function in an OpenTelemetry span."""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer("aios.tracing")
            with tracer.start_as_current_span(
                name,
                kind=kind,
                attributes=attributes or {},
            ) as span:
                start = time.monotonic()
                try:
                    result = fn(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    span.record_exception(exc)
                    raise
                finally:
                    span.set_attribute("duration_ms", (time.monotonic() - start) * 1000)

        return wrapper  # type: ignore[return-value]

    return decorator


__all__ = [
    "SpanKind",
    "get_tracer",
    "init_tracing",
    "reset_tracing",
    "trace_operation",
    "trace_sync",
]
