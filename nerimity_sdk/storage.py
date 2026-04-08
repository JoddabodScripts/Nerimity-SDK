"""Persistent key/value storage abstraction.

Backends: JSON (default), SQLite, Redis.

Usage::

    # JSON (default)
    bot = Bot(token="...", store=JsonStore("data.json"))

    # SQLite
    bot = Bot(token="...", store=SqliteStore("bot.db"))

    # Redis
    bot = Bot(token="...", store=RedisStore(redis_client))

    # In commands:
    prefix = await bot.store.get(f"guild:{ctx.server_id}:prefix") or "!"
    await bot.store.set(f"guild:{ctx.server_id}:prefix", "?")
"""
from __future__ import annotations
import asyncio
import json
import os
from typing import Any, Optional, Protocol


class Store(Protocol):
    async def get(self, key: str) -> Optional[Any]: ...
    async def set(self, key: str, value: Any) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def keys(self, pattern: str = "*") -> list[str]: ...


class JsonStore:
    """Simple JSON file backend. Fine for single-process bots."""

    def __init__(self, path: str = "bot_data.json") -> None:
        self._path = path
        self._data: dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._path):
            with open(self._path) as f:
                self._data = json.load(f)

    def _save(self) -> None:
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    async def get(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._data[key] = value
            self._save()

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._data.pop(key, None)
            self._save()

    async def keys(self, pattern: str = "*") -> list[str]:
        import fnmatch
        return [k for k in self._data if fnmatch.fnmatch(k, pattern)]


class SqliteStore:
    """SQLite backend using aiosqlite (install separately: pip install aiosqlite)."""

    def __init__(self, path: str = "bot.db") -> None:
        self._path = path
        self._db = None

    async def _conn(self):
        if self._db is None:
            import aiosqlite
            self._db = await aiosqlite.connect(self._path)
            await self._db.execute(
                "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)"
            )
            await self._db.commit()
        return self._db

    async def get(self, key: str) -> Optional[Any]:
        db = await self._conn()
        async with db.execute("SELECT value FROM kv WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
        return json.loads(row[0]) if row else None

    async def set(self, key: str, value: Any) -> None:
        db = await self._conn()
        await db.execute(
            "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)",
            (key, json.dumps(value))
        )
        await db.commit()

    async def delete(self, key: str) -> None:
        db = await self._conn()
        await db.execute("DELETE FROM kv WHERE key=?", (key,))
        await db.commit()

    async def keys(self, pattern: str = "*") -> list[str]:
        import fnmatch
        db = await self._conn()
        async with db.execute("SELECT key FROM kv") as cur:
            rows = await cur.fetchall()
        return [r[0] for r in rows if fnmatch.fnmatch(r[0], pattern)]


class RedisStore:
    """Redis backend. Pass an async redis client (e.g. from `redis.asyncio`)."""

    def __init__(self, client: Any, prefix: str = "nerimity:") -> None:
        self._r = client
        self._prefix = prefix

    def _k(self, key: str) -> str:
        return f"{self._prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        raw = await self._r.get(self._k(key))
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: Any) -> None:
        await self._r.set(self._k(key), json.dumps(value))

    async def delete(self, key: str) -> None:
        await self._r.delete(self._k(key))

    async def keys(self, pattern: str = "*") -> list[str]:
        raw = await self._r.keys(f"{self._prefix}{pattern}")
        return [k.decode().removeprefix(self._prefix) for k in raw]


class MemoryStore:
    """In-memory store (no persistence). Useful for testing."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def get(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    async def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def keys(self, pattern: str = "*") -> list[str]:
        import fnmatch
        return [k for k in self._data if fnmatch.fnmatch(k, pattern)]
