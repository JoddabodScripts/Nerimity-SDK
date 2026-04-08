# Configuration

All options are passed to the `Bot` constructor.

```python
bot = Bot(
    token="YOUR_TOKEN",          # required
    prefix="!",                  # default command prefix
    prefix_store=None,           # pluggable per-guild prefix backend
    cache_size=1000,             # max objects per cache type
    cache_ttl=0,                 # TTL in seconds (0 = no expiry)
    cache_invalidate_on_disconnect=True,  # wipe cache on disconnect
    debug=False,                 # pretty-print all gateway payloads
    watch=False,                 # auto-reload plugins on file save
    watch_paths=["plugins"],     # directories to watch
    store=None,                  # persistent storage backend
    shard_id=0,                  # shard index (future use)
    shard_count=1,               # total shards (future use)
)
```

## Per-guild prefix

```python
from nerimity_sdk import MemoryPrefixStore

bot = Bot(token="...", prefix="!")

# At runtime:
await bot.prefix_resolver.set("guild_id", "?")
await bot.prefix_resolver.reset("guild_id")   # back to default
```

## Storage backends

```python
from nerimity_sdk import JsonStore, SqliteStore, RedisStore, MemoryStore

bot = Bot(token="...", store=JsonStore("data.json"))   # default
bot = Bot(token="...", store=SqliteStore("bot.db"))    # pip install aiosqlite
bot = Bot(token="...", store=RedisStore(redis_client)) # pip install redis
bot = Bot(token="...", store=MemoryStore())            # no persistence
```

## Debug mode

```python
bot = Bot(token="...", debug=True)
```

Logs every raw gateway payload with pretty JSON formatting. Useful when reverse-engineering undocumented events.

## Watch mode

```python
bot = Bot(token="...", watch=True, watch_paths=["plugins"])
```

Requires `pip install watchfiles`. Automatically reloads plugins when their `.py` file changes on disk.
