# Cache

In-memory LRU/TTL cache for all Nerimity objects.

## Accessing cached objects

```python
server  = bot.cache.servers.get("server_id")
channel = bot.cache.channels.get("channel_id")
user    = bot.cache.users.get("user_id")
member  = bot.cache.members.get("server_id:user_id")
message = bot.cache.messages.get("message_id")
```

## Partial merge

Gateway events often send partial objects. The cache merges them intelligently — a `{id, username}` update won't wipe the avatar field.

## Configuration

```python
bot = Bot(
    token="...",
    cache_size=1000,   # max objects per type
    cache_ttl=3600,    # expire after 1 hour (0 = never)
    cache_invalidate_on_disconnect=True,  # wipe on reconnect
)
```

## Redis adapter

For multi-process bots, use the Redis adapter:

```python
import redis.asyncio as aioredis
from nerimity_sdk.cache.redis_adapter import RedisCache

r = aioredis.from_url("redis://localhost")
cache = RedisCache(r, prefix="mybot:", ttl=3600)
```
