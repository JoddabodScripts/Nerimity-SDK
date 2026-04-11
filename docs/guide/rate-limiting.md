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
- You're running **multiple shards** hitting the same routes — the rate limit manager is per-process, so shards don't coordinate with each other. Use Redis-backed rate limit tracking if this matters
- You're calling REST methods in a tight loop — add a small delay between calls

```python
import asyncio

for channel_id in channel_ids:
    await bot.rest.send_message(channel_id, "Announcement!")
    await asyncio.sleep(0.5)   # avoid hammering the API
```

---

## Adjusting the request timeout

The default request timeout is 30 seconds. Increase it if you're on a slow connection or hitting large endpoints:

```python
bot.rest.timeout = 60.0
```
