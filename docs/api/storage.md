# Storage

A simple async key-value store. All backends implement the same interface.

## Interface

```python
await bot.store.get("key")           # → Any | None
await bot.store.set("key", value)    # value can be any JSON-serializable type
await bot.store.delete("key")
await bot.store.keys("guild:*")      # fnmatch pattern → list[str]
```

## Backends

### MemoryStore (default)
No persistence. Useful for testing.

```python
from nerimity_sdk import MemoryStore
bot = Bot(token="...", store=MemoryStore())
```

### JsonStore
Persists to a JSON file. Zero extra dependencies.

```python
from nerimity_sdk import JsonStore
bot = Bot(token="...", store=JsonStore("data.json"))
```

### SqliteStore
Async SQLite. Requires `pip install aiosqlite`.

```python
from nerimity_sdk import SqliteStore
bot = Bot(token="...", store=SqliteStore("bot.db"))
```

### RedisStore
Async Redis. Requires `pip install redis`.

```python
import redis.asyncio as aioredis
from nerimity_sdk import RedisStore

r = aioredis.from_url("redis://localhost")
bot = Bot(token="...", store=RedisStore(r, prefix="mybot:"))
```

## Common patterns

```python
# Per-guild settings
prefix = await bot.store.get(f"guild:{ctx.server_id}:prefix") or "!"
await bot.store.set(f"guild:{ctx.server_id}:prefix", "?")

# User data
await bot.store.set(f"user:{ctx.author.id}:xp", 100)

# List all guild prefixes
keys = await bot.store.keys("guild:*:prefix")
```
