# Utilities

## Mentions

Nerimity uses `[@:user_id]` syntax for mentions.

```python
from nerimity_sdk import mention, parse_mention_ids, resolve_mentions

# Format a user ID as a mention
mention("123456789")   # → "[@:123456789]"

# Extract all user IDs from a string
parse_mention_ids("Hello [@:111] and [@:222]")   # → ["111", "222"]

# Resolve mentions to cached User objects
users = resolve_mentions(message.content, bot.cache)
```

### `ctx.mentions`

The `Context` object exposes a `mentions` property that automatically resolves all `[@:id]` mentions in the triggering message:

```python
@bot.command("ping_all")
async def ping_all(ctx):
    for user in ctx.mentions:
        await ctx.reply(f"Pinging {user.username}!")
```

## Paginator

```python
from nerimity_sdk import Paginator

pages = ["Page 1 content", "Page 2 content", "Page 3 content"]
await Paginator(pages, timeout=60).send(ctx)
```

- If a `ButtonRouter` is wired (it is by default in bot commands), navigation uses prev/next buttons with the given TTL.
- Otherwise falls back to text-based `next`/`prev`/`stop` prompts via `ctx.ask()`.

## MessageBuilder

```python
from nerimity_sdk import MessageBuilder

await (MessageBuilder()
    .content("Hello!")
    .reply_to("message_id")
    .silent()
    .send(ctx.rest, ctx.channel_id))
```

## Embed

```python
from nerimity_sdk import Embed

embed = (Embed()
    .title("Server Info")
    .description("Some details here")
    .url("https://nerimity.com")
    .image("https://example.com/image.png")
    .color(0x5865F2))

d = embed.to_dict()   # serialize to dict for API calls
```
