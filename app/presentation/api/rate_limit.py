"""A simple in-process sliding-window rate limiter.

Per-process, in-memory: fine for a single API instance; a multi-instance deployment
would need a shared store (e.g. Redis) instead.
"""
import time
from collections import deque
from threading import Lock


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float, clock=time.monotonic) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque] = {}
        self._lock = Lock()

    def check(self, key: str) -> tuple[bool, int, float]:
        """Returns (allowed, remaining, retry_after_seconds). Always records the
        attempt's timestamp so a caller that ignores a False result cannot bypass
        the window by retrying immediately."""
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self._window:
                hits.popleft()
            allowed = len(hits) < self._max
            if allowed:
                hits.append(now)
                remaining = self._max - len(hits)
                return True, remaining, 0.0
            retry_after = self._window - (now - hits[0])
            return False, 0, max(retry_after, 0.0)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
