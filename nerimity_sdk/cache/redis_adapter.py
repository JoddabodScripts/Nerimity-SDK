"""Optional Redis adapter for multi-process bots."""
from __future__ import annotations
import json
from typing import Any, Optional


class RedisCache:
    """Drop-in replacement for LRUCache backed by Redis."""

    def __init__(self, redis_client: Any, prefix: str = "nerimity:", ttl: int = 3600) -> None:
        self._r = redis_client
        self._prefix = prefix
        self._ttl = ttl

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    async def get(self, key: str) -> Optional[dict]:
        raw = await self._r.get(self._key(key))
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: Any) -> None:
        data = value if isinstance(value, str) else json.dumps(value, default=str)
        await self._r.set(self._key(key), data, ex=self._ttl)

    async def delete(self, key: str) -> None:
        await self._r.delete(self._key(key))
