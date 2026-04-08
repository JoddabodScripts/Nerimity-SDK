# nerimity-sdk

A fully-featured Python SDK for building [Nerimity](https://nerimity.com) bots. Think discord.py, but for Nerimity.

```bash
pip install nerimity-sdk
```

## Features at a glance

| Feature | Description |
|---|---|
| **Typed events** | Every gateway event is a dataclass — full autocomplete, no raw dicts |
| **Prefix commands** | Arg parsing, converters, middleware, cooldowns, help generator |
| **Slash commands** | `@bot.slash("ban")` — register + handle in one place |
| **Buttons** | Pattern-matched button handlers with TTL |
| **Paginator** | Multi-page responses with prev/next navigation |
| **ctx.confirm()** | Yes/no confirmation for destructive commands |
| **ctx.ask()** | Multi-step conversation helpers with timeout |
| **Mentions** | Parse `[@:id]` ↔ user objects, `mention(user_id)` helper |
| **Cache** | LRU/TTL cache with partial merge, optional Redis |
| **Permissions** | Declarative flag checks + role hierarchy |
| **Plugins** | Hot-reload modules at runtime |
| **Storage** | JSON / SQLite / Redis key-value store |
| **Scheduler** | `@bot.cron("0 9 * * *")` backed by croniter |
| **Error handlers** | `@bot.on_command_error`, `on_slash_error`, `on_button_error` |
| **Dev tools** | `debug=True`, `watch=True`, `MockBot` for unit tests |
| **CLI** | `nerimity create my-bot` scaffolds a project |

## Quick example

```python
from nerimity_sdk import Bot, Int

bot = Bot(token="YOUR_TOKEN", prefix="!")

@bot.on("ready")
async def on_ready(me):
    print(f"Logged in as {me.username}#{me.tag}")

@bot.command("add", args=[Int, Int])
async def add(ctx):
    a, b = ctx.args
    await ctx.reply(f"{a} + {b} = {a + b}")

bot.run()
```

See the [Getting Started guide](guide/installation.md) or jump straight to the [Example Bot](example.md).
