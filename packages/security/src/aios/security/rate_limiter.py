"""Rate limiter — sliding window and token bucket algorithms."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


class RateLimitExceeded(Exception):  # noqa: N818
    """Raised when a rate limit is exceeded."""


@dataclass
class RateLimiter:
    """Token bucket rate limiter.

    Attributes:
        capacity: Maximum number of tokens (burst size).
        refill_rate: Tokens added per second.
    """

    capacity: int = 10
    refill_rate: float = 1.0
    _tokens: float = field(init=False, default=0.0)
    _last_refill: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        self._tokens = float(self.capacity)
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now

    def allow(self, cost: int = 1) -> bool:
        """Try to consume *cost* tokens. Returns True if allowed."""
        self._refill()
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False

    def deny(self, cost: int = 1) -> None:
        """Try to consume tokens; raises RateLimitExceeded on failure."""
        if not self.allow(cost):
            raise RateLimitExceeded(
                f"Rate limit exceeded: need {cost} tokens, "
                f"{self._tokens:.1f} remaining"
            )

    @property
    def remaining(self) -> float:
        self._refill()
        return self._tokens

    def reset(self) -> None:
        """Reset to full capacity."""
        self._tokens = float(self.capacity)
        self._last_refill = time.monotonic()


@dataclass
class SlidingWindowLimiter:
    """Sliding window rate limiter using a timestamp deque.

    Attributes:
        max_requests: Maximum requests in the window.
        window_seconds: Window duration in seconds.
    """

    max_requests: int = 10
    window_seconds: float = 60.0
    _timestamps: deque[float] = field(default_factory=deque, init=False)

    def _cleanup(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def allow(self, cost: int = 1) -> bool:
        """Check if *cost* requests are allowed in the current window."""
        now = time.monotonic()
        self._cleanup(now)
        if len(self._timestamps) + cost <= self.max_requests:
            for _ in range(cost):
                self._timestamps.append(now)
            return True
        return False

    def deny(self, cost: int = 1) -> None:
        """Try; raises RateLimitExceeded on failure."""
        if not self.allow(cost):
            raise RateLimitExceeded(
                f"Sliding window limit: {self.max_requests} reqs / "
                f"{self.window_seconds}s exceeded"
            )

    @property
    def current_count(self) -> int:
        now = time.monotonic()
        self._cleanup(now)
        return len(self._timestamps)

    def reset(self) -> None:
        """Clear all timestamps."""
        self._timestamps.clear()
