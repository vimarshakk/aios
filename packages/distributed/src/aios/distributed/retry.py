"""Retry policies with exponential backoff, jitter, and configurable strategies.

Provides composable retry policies that integrate with the worker framework
for automatic task retry on transient failures.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted.

    Attributes:
        last_exception: The final exception that caused the failure.
        attempts: Total number of attempts made.
        task_id: The ID of the failed task.
    """

    def __init__(self, last_exception: Exception, attempts: int, task_id: str) -> None:
        self.last_exception = last_exception
        self.attempts = attempts
        self.task_id = task_id
        super().__init__(
            f"Retry exhausted after {attempts} attempts for task {task_id}: {last_exception}"
        )


@dataclass
class ExponentialBackoff:
    """Exponential backoff configuration.

    Attributes:
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay cap in seconds.
        multiplier: Growth factor per retry.
        jitter: Whether to add random jitter to the delay.
        jitter_range: Max fraction of jitter (0.0-1.0).
    """

    base_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.5

    def delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number (0-based).

        Args:
            attempt: Current attempt number (0 = first retry).

        Returns:
            Delay in seconds before the next retry.
        """
        delay = min(self.base_delay * (self.multiplier ** attempt), self.max_delay)
        if self.jitter:
            jitter_amount = delay * self.jitter_range
            delay += random.uniform(-jitter_amount, jitter_amount)  # noqa: S311
            delay = max(0.1, delay)
        return delay


class RetryPolicy:
    """Configurable retry policy with strategy support.

    Strategies:
        - "exponential": Exponential backoff with jitter (default).
        - "linear": Linear backoff (delay = base_delay * attempt).
        - "fixed": Fixed delay between retries.
        - "immediate": No delay between retries.

    Usage::

        policy = RetryPolicy(max_retries=3, backoff=ExponentialBackoff())
        for attempt in range(policy.max_retries):
            delay = policy.delay_for_attempt(attempt)
            ...
    """

    def __init__(
        self,
        max_retries: int = 3,
        backoff: ExponentialBackoff | None = None,
        strategy: str = "exponential",
        retryable_exceptions: tuple[type[Exception], ...] | None = None,
        non_retryable_exceptions: tuple[type[Exception], ...] | None = None,
        on_retry: Any = None,
    ) -> None:
        self.max_retries = max_retries
        self.backoff = backoff or ExponentialBackoff()
        self.strategy = strategy
        self.retryable_exceptions = retryable_exceptions
        self.non_retryable_exceptions = non_retryable_exceptions or (ValueError, TypeError)
        self.on_retry = on_retry

    def delay_for_attempt(self, attempt: int) -> float:
        """Calculate delay for the given attempt number.

        Args:
            attempt: 0-based attempt number.

        Returns:
            Delay in seconds.
        """
        if self.strategy == "fixed":
            return self.backoff.base_delay
        if self.strategy == "linear":
            return min(self.backoff.base_delay * (attempt + 1), self.backoff.max_delay)
        if self.strategy == "immediate":
            return 0.0
        return self.backoff.delay(attempt)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if the exception should trigger a retry.

        Args:
            exception: The exception that was raised.
            attempt: Current attempt number (0-based).

        Returns:
            True if the task should be retried.
        """
        if attempt >= self.max_retries:
            return False
        if self.non_retryable_exceptions and isinstance(exception, self.non_retryable_exceptions):
            return False
        if self.retryable_exceptions is not None:
            return isinstance(exception, self.retryable_exceptions)
        return True

    def time_until_retry(self, attempt: int) -> float:
        """Get the time to sleep before the next retry attempt.

        Args:
            attempt: Current attempt number (0-based).

        Returns:
            Seconds to sleep.
        """
        return max(0.0, self.delay_for_attempt(attempt))

    def total_retry_time(self) -> float:
        """Calculate the total time spent retrying across all attempts.

        Returns:
            Total retry time in seconds.
        """
        return sum(self.delay_for_attempt(i) for i in range(self.max_retries))


__all__ = [
    "ExponentialBackoff",
    "RetryExhaustedError",
    "RetryPolicy",
]
