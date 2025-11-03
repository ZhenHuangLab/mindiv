from __future__ import annotations
from typing import Any, Dict, Optional
import asyncio
import time

class RateLimitError(Exception):
    pass

class TokenBucket:
    """
    Async token bucket with QPS (tokens/sec) refill and burst capacity.
    acquire(tokens=1, timeout=None, strategy='wait'|'fail')
    """
    def __init__(self, qps: float, burst: int, *, clock=time.monotonic) -> None:
        assert qps >= 0, "qps must be non-negative"
        assert burst >= 0, "burst must be non-negative"
        self.qps = float(qps)
        self.burst = float(burst)
        self._tokens = float(burst)
        self._last = clock()
        self._lock = asyncio.Lock()
        self._clock = clock

    async def acquire(self, tokens: float = 1.0, *, timeout: Optional[float] = None, strategy: str = "wait") -> None:
        if tokens <= 0:
            return
        start = self._clock()
        async with self._lock:
            while True:
                now = self._clock()
                elapsed = now - self._last
                if elapsed > 0:
                    self._tokens = min(self.burst, self._tokens + elapsed * self.qps)
                    self._last = now
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                # Not enough tokens
                if strategy == "fail":
                    raise RateLimitError("Rate limit exceeded (token bucket)")
                # strategy == 'wait'
                needed = tokens - self._tokens
                # compute wait time for next token availability
                wait_time = needed / (self.qps if self.qps > 0 else 1e-9)
                if timeout is not None and (self._clock() - start + wait_time) > timeout:
                    raise RateLimitError("Rate limit timeout (token bucket)")
                await asyncio.sleep(min(wait_time, 0.5))

class WindowRateLimiter:
    """
    Fixed window async rate limiter for at most N events per window seconds.
    Less smooth than token bucket; useful for strict per-window caps.
    """
    def __init__(self, limit: int, window: float) -> None:
        assert limit >= 0 and window > 0
        self.limit = int(limit)
        self.window = float(window)
        self._count = 0
        self._window_start = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, *, timeout: Optional[float] = None, strategy: str = "wait") -> None:
        start = time.monotonic()
        async with self._lock:
            while True:
                now = time.monotonic()
                if now - self._window_start >= self.window:
                    self._window_start = now
                    self._count = 0
                if self._count < self.limit:
                    self._count += 1
                    return
                if strategy == "fail":
                    raise RateLimitError("Rate limit exceeded (window)")
                # wait until window resets
                sleep_for = (self.window - (now - self._window_start))
                if sleep_for < 0:
                    sleep_for = 0
                if timeout is not None and (time.monotonic() - start + sleep_for) > timeout:
                    raise RateLimitError("Rate limit timeout (window)")
                await asyncio.sleep(min(sleep_for, 0.5))

class GlobalRateLimiter:
    """
    Manages multiple buckets keyed by dimension, e.g., provider:model:tenant.
    Coordinates token buckets with optional window limiter.
    Thread-unsafe across processes; for multi-instance deployments use Redis.
    """
    def __init__(self) -> None:
        self._buckets: Dict[str, TokenBucket] = {}
        self._windows: Dict[str, WindowRateLimiter] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def make_key(*parts: Optional[str]) -> str:
        return ":".join(p for p in parts if p)

    async def configure_bucket(self, key: str, qps: float, burst: int) -> None:
        async with self._lock:
            self._buckets[key] = TokenBucket(qps=qps, burst=burst)

    async def configure_window(self, key: str, limit: int, window_seconds: float) -> None:
        async with self._lock:
            self._windows[key] = WindowRateLimiter(limit=limit, window=window_seconds)

    async def acquire(self, key: str, tokens: float = 1.0, *, timeout: Optional[float] = None, strategy: str = "wait") -> None:
        # Token bucket first for smoothing
        bucket = self._buckets.get(key)
        if bucket is not None:
            await bucket.acquire(tokens=tokens, timeout=timeout, strategy=strategy)
        # Then strict window, if configured
        window = self._windows.get(key)
        if window is not None:
            await window.acquire(timeout=timeout, strategy=strategy)

# Singleton helper
_global_limiter: Optional[GlobalRateLimiter] = None

def get_global_rate_limiter() -> GlobalRateLimiter:
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = GlobalRateLimiter()
    return _global_limiter

