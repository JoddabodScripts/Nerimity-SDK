# Rate Limiting

Nerimity's API enforces rate limits on HTTP requests. The SDK handles these automatically — you don't need to do anything for basic usage.

---

## How the SDK handles it

Every request through `bot.rest` goes through a rate limit manager that:

1. Tracks the `X-RateLimit-*` headers on every response
2. Queues requests that would exceed the limit and retries them after the reset window
3. Handles global rate limits (which apply across all routes) separately from per-route limits

This means your code will never see a `429` error under normal conditions — the SDK just waits and retries transparently.

---

## The rate limit hook

If you want to observe or log rate limit events:

```python
@bot.on_ratelimit
async def on_ratelimit(route, retry_after):
    print(f"Rate limited on {route}, retrying in {retry_after:.2f}s")
```

| Parameter | Type | Description |
|---|---|---|
| `route` | `str` | The API route that was rate limited (e.g. `POST /messages`) |
| `retry_after` | `float` | Seconds until the limit resets |

This fires every time the SDK hits a rate limit, before it retries. Useful for monitoring or alerting.

---

## When you need to care

The automatic handling covers most cases. You may need to think about rate limits if:

- You're sending **bulk messages** (e.g. announcing to many channels at once) — space them out manually or use `asyncio.sleep`
- You're running **multiple shards** hitting the same routes — the rate limit manager is per-process by default, so shards don't coordinate with each other. Use the Redis backend if this matters (see below)
- You're calling REST methods in a tight loop — add a small delay between calls

```python
import asyncio

for channel_id in channel_ids:
    await bot.rest.send_message(channel_id, "Announcement!")
    await asyncio.sleep(0.5)   # avoid hammering the API
```

---

## Distributed rate limiting (multi-shard / multi-process)

By default the rate limiter is in-process — each shard tracks its own buckets independently. If you're running multiple shards as separate processes, they can each exhaust the same route bucket without knowing about each other.

Use `RedisRateLimiter` to share rate limit state across all processes:

```python
from nerimity_sdk import Bot, RedisRateLimiter

bot = Bot(
    token="...",
    rate_limiter=RedisRateLimiter("redis://localhost:6379"),
)
```

Requires:
```
pip install "nerimity-sdk[redis]"
```

All bot processes pointing at the same Redis instance will coordinate — if one shard exhausts a bucket, the others will wait correctly instead of all hitting 429 at once.

You can also implement your own backend by subclassing `RateLimitBackend`:

```python
from nerimity_sdk import RateLimitBackend

class MyBackend(RateLimitBackend):
    async def acquire(self, key): ...
    async def update(self, key, remaining, reset_at): ...
    async def acquire_global(self): ...
    async def set_global_reset(self, reset_at): ...
```

---

## Adjusting the request timeout

The default request timeout is 30 seconds. Increase it if you're on a slow connection or hitting large endpoints:

```python
bot.rest.timeout = 60.0
```
