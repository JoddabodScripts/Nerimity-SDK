# Configuration

All options are passed to the `Bot` constructor.

```python
bot = Bot(
    token="YOUR_TOKEN",          # required
    prefix="/",                  # default command prefix (/ = native slash)
    prefix_store=None,           # pluggable per-guild prefix backend
    cache_size=1000,             # max objects per cache type
    cache_ttl=0,                 # TTL in seconds (0 = no expiry)
    cache_invalidate_on_disconnect=True,  # wipe cache on disconnect
    debug=False,                 # pretty-print all gateway payloads
    json_logs=False,             # structured JSON log output (for Docker/cloud)
    health_port=None,            # expose /health and /stats HTTP endpoints on this port
    watch=False,                 # hot-reload plugins on file save (legacy)
    watch_paths=["plugins"],     # directories to watch
    store=None,                  # persistent storage backend
    shard_id=0,                  # shard index (future use)
    shard_count=1,               # total shards (future use)
)
```

## Auto-restart

`bot.run()` automatically wraps your script in a watchdog process that:
- Restarts the bot if it crashes
- Restarts the bot when any `.py` file in the project is saved

To disable:

```python
bot.run(auto_restart=False)
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

## JSON logging

```python
bot = Bot(token="...", json_logs=True)
```

Outputs every log line as a JSON object — useful for bots running in Docker or cloud environments where logs are piped to a collector (Datadog, CloudWatch, etc.).

## Runtime stats

```python
print(bot.stats)
# {
#   "uptime_seconds": 3600.0,
#   "messages_seen": 1234,
#   "commands_dispatched": 56,
#   "cached_users": 200,
#   "cached_servers": 5,
#   "cached_channels": 40,
#   "cached_members": 300,
# }
```

## Watch mode (legacy)

```python
bot = Bot(token="...", watch=True, watch_paths=["plugins"])
```

Requires `pip install watchfiles`. Hot-reloads plugin classes when their `.py` file changes. For full process restart on any file change, `bot.run()` handles this automatically without any extra config.
