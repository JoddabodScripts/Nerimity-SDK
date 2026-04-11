"""Distributed rate limit backends for multi-process / multi-shard bots."""
from __future__ import annotations
import asyncio
import time
from abc import ABC, abstractmethod
from typing import Optional


class RateLimitBackend(ABC):
    """Abstract rate limit backend. Swap in any implementation via Bot(rate_limiter=...)."""

    @abstractmethod
    async def acquire(self, key: str) -> None:
        """Block until a request on *key* is allowed."""

    @abstractmethod
    async def update(self, key: str, remaining: int, reset_at: float) -> None:
        """Record the rate limit state returned by the server for *key*."""

    @abstractmethod
    async def acquire_global(self) -> None:
        """Block until the global rate limit has cleared."""

    @abstractmethod
    async def set_global_reset(self, reset_at: float) -> None:
        """Record a global rate limit reset timestamp."""

    async def close(self) -> None:  # noqa: B027
        pass


class LocalRateLimitBackend(RateLimitBackend):
    """Default in-process backend — same behaviour as before, zero dependencies."""

    def __init__(self) -> None:
        self._buckets: dict[str, tuple[int, float]] = {}  # key -> (remaining, reset_at)
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_reset: float = 0.0
        self._global_lock = asyncio.Lock()

    def _lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    async def acquire(self, key: str) -> None:
        async with self._lock(key):
            remaining, reset_at = self._buckets.get(key, (1, 0.0))
            if remaining <= 0:
                wait = reset_at - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
            self._buckets[key] = (max(0, remaining - 1), reset_at)

    async def update(self, key: str, remaining: int, reset_at: float) -> None:
        self._buckets[key] = (remaining, reset_at)

    async def acquire_global(self) -> None:
        async with self._global_lock:
            wait = self._global_reset - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)

    async def set_global_reset(self, reset_at: float) -> None:
        self._global_reset = reset_at


class RedisRateLimiter(RateLimitBackend):
    """
    Redis-backed distributed rate limiter. Safe across multiple processes and shards.

    Requires: pip install "nerimity-sdk[redis]"

    Usage::

        from nerimity_sdk import Bot, RedisRateLimiter

        bot = Bot(
            token="...",
            rate_limiter=RedisRateLimiter("redis://localhost:6379"),
        )
    """

    _PREFIX = "nerimity:rl:"
    _GLOBAL_KEY = "nerimity:rl:global"

    def __init__(self, url: str = "redis://localhost:6379", *, ttl: int = 10) -> None:
        self._url = url
        self._ttl = ttl
        self._redis: Optional[object] = None
        self._local_locks: dict[str, asyncio.Lock] = {}

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
            except ImportError:
                raise RuntimeError(
                    'Redis support requires: pip install "nerimity-sdk[redis]"'
                )
            self._redis = await aioredis.from_url(self._url, decode_responses=True)
        return self._redis

    def _lock(self, key: str) -> asyncio.Lock:
        if key not in self._local_locks:
            self._local_locks[key] = asyncio.Lock()
        return self._local_locks[key]

    async def acquire(self, key: str) -> None:
        async with self._lock(key):
            r = await self._get_redis()
            rkey = self._PREFIX + key
            data = await r.hmget(rkey, "remaining", "reset_at")
            remaining = int(data[0]) if data[0] is not None else 1
            reset_at = float(data[1]) if data[1] is not None else 0.0

            if remaining <= 0:
                wait = reset_at - time.time()
                if wait > 0:
                    await asyncio.sleep(wait)

            await r.hset(rkey, "remaining", max(0, remaining - 1))
            await r.expire(rkey, self._ttl)

    async def update(self, key: str, remaining: int, reset_at: float) -> None:
        r = await self._get_redis()
        rkey = self._PREFIX + key
        await r.hset(rkey, mapping={"remaining": remaining, "reset_at": reset_at})
        await r.expire(rkey, self._ttl)

    async def acquire_global(self) -> None:
        r = await self._get_redis()
        val = await r.get(self._GLOBAL_KEY)
        if val is not None:
            wait = float(val) - time.time()
            if wait > 0:
                await asyncio.sleep(wait)

    async def set_global_reset(self, reset_at: float) -> None:
        r = await self._get_redis()
        ttl = max(1, int(reset_at - time.time()) + 1)
        await r.set(self._GLOBAL_KEY, reset_at, ex=ttl)

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
