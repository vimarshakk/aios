"""RetryPolicy — Exponential backoff and retry configuration."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


@dataclass
class RetryPolicy:
    """Configures retry behaviour for failed workflow steps.

    Attributes:
        max_retries: Maximum number of retry attempts (0 = no retries).
        base_delay: Base delay in seconds before the first retry.
        max_delay: Upper bound on the delay between retries.
        backoff_factor: Multiplier applied to the delay after each retry.
        jitter: If True, add random jitter (0-25% of delay) to avoid thundering herd.
        retryable_errors: Optional tuple of exception types that trigger a retry.
            If empty/None, all exceptions are retryable.
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retryable_errors: tuple[type[Exception], ...] = field(default_factory=tuple)

    def delay_for_attempt(self, attempt: int) -> float:
        """Compute the delay in seconds for a given retry attempt (0-indexed).

        Uses exponential backoff: base_delay * (backoff_factor ** attempt),
        capped at max_delay. Adds jitter when enabled.
        """
        delay = self.base_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay += random.uniform(0, delay * 0.25)  # noqa: S311
        return delay

    def should_retry(self, attempt: int, error: Exception | None = None) -> bool:
        """Return True if another retry is allowed.

        Args:
            attempt: Current attempt number (0-indexed). attempt=0 means first failure.
            error: The exception that caused the failure (used to check retryable_errors).
        """
        if attempt >= self.max_retries:
            return False
        if self.retryable_errors and error is not None:
            return isinstance(error, self.retryable_errors)
        return True

    async def execute_with_retry(
        self,
        fn: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute an async callable with retry logic.

        Returns the result on success, or raises the last exception on final failure.
        """
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                last_error = exc
                if not self.should_retry(attempt, exc):
                    raise
                delay = self.delay_for_attempt(attempt)
                await asyncio.sleep(delay)
        if last_error is not None:
            raise last_error
        return None  # pragma: no cover
