# Sharding

Sharding splits a bot's server connections across multiple processes. Each shard handles a subset of servers.

You only need sharding if your bot is in a large number of servers. For most bots, a single process is fine.

---

## When to shard

Nerimity's gateway has a connection limit per token. Once your bot reaches that limit, the gateway will reject new connections until you shard. The SDK will log a warning when you're approaching the limit.

---

## How it works

Each shard is identified by two numbers: its **shard ID** (0-indexed) and the **total shard count**. The gateway uses these to divide servers evenly — shard `n` receives events only for servers where `server_id % shard_count == n`.

---

## Running a sharded bot

Use `Bot.from_shard()` instead of `Bot()`:

```python
import sys
from nerimity_sdk import Bot

shard_id    = int(sys.argv[1])   # e.g. 0, 1, 2 ...
shard_count = int(sys.argv[2])   # total number of shards

bot = Bot.from_shard(
    token="YOUR_TOKEN",
    shard_id=shard_id,
    shard_count=shard_count,
)

@bot.on("ready")
async def on_ready(me):
    print(f"Shard {shard_id}/{shard_count} ready")

bot.run()
```

Run each shard as a separate process:

```
python bot.py 0 4
python bot.py 1 4
python bot.py 2 4
python bot.py 3 4
```

---

## What changes with sharding

- Each shard only receives events for its subset of servers — `bot.cache` only contains data for those servers
- `bot.rest` works normally on all shards — REST calls are not sharded
- The built-in `/stats` command reports per-shard stats
- Plugins, storage, and scheduled tasks work the same way on each shard

---

## Coordinating shards

If you need shards to share state (e.g. a global cooldown or cross-server leaderboard), use a shared storage backend:

```python
from nerimity_sdk import Bot, RedisStore

bot = Bot.from_shard(
    token="YOUR_TOKEN",
    shard_id=shard_id,
    shard_count=shard_count,
    store=RedisStore("redis://localhost:6379"),
)
```

All shards pointing at the same Redis instance will share the same key-value store.

---

## Auto-sharding

Pass `shard_count="auto"` to let the SDK ask the gateway how many shards to use:

```python
bot = Bot.from_shard(token="YOUR_TOKEN", shard_id=0, shard_count="auto")
```

This is only useful if you're running a single shard process and want the gateway to decide the total count.
