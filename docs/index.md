# nerimity-sdk

A Python library for building bots on [Nerimity](https://nerimity.com).

```bash
pip install nerimity-sdk
```

## How it works

You create a `Bot`, attach handlers with decorators, then call `bot.run()`.
The bot connects over a WebSocket, receives events, and dispatches them to your handlers.

```
Nerimity → WebSocket → GatewayClient → EventEmitter → your handlers
```

Everything your handlers need is in the `ctx` object passed to them.

## Quickstart

**Get a token:** [nerimity.com/app/settings/developer/applications](https://nerimity.com/app/settings/developer/applications) → create app → add Bot → copy token.

```bash
nerimity create my-bot
cd my-bot && cp .env.example .env   # open .env and paste token
python bot.py
```

Or manually:

```python
import os
from dotenv import load_dotenv
from nerimity_sdk import Bot

load_dotenv()
bot = Bot(token=os.environ["NERIMITY_TOKEN"]) # or make a .env file with this in it NERIMITY_TOKEN=your_token

@bot.on("ready")
async def on_ready(me):
    print(f"Logged in as {me.username}#{me.tag}")

@bot.command("ping", description="Replies with Pong!")
async def ping(ctx):
    await ctx.reply("Pong!")

bot.run()
```

## What's available

| Feature | How to use |
|---|---|
| Event listeners | `@bot.on("message:created")` |
| Prefix + slash commands | `@bot.command("ping")` — works as `/ping` (default) |
| Prefix-only commands | `@bot.command_private("debug")` |
| Argument converters | `args=[Int, MemberConverter]` or type annotations |
| Type annotation converters | `async def add(ctx, a: int, b: int)` — no `args=` needed |
| Permission shortcut | `@bot.command("ban", requires=Permissions.BAN_MEMBERS)` |
| Confirmation prompts | `await ctx.confirm("Sure?")` |
| Multi-step conversations | `await ctx.ask("Your name?")` |
| DMs | `await ctx.author.send(bot.rest, "Hi!")` |
| Edit messages | `await ctx.edit(msg.id, "updated!")` |
| File uploads | `await ctx.reply_file("image.png")` |
| Embeds | `await ctx.reply_embed(Embed().title("Hi"))` |
| Pin messages | `await ctx.pin()` |
| Paginator | `await Paginator(pages).send(ctx)` |
| Mention helpers | `mention(user_id)` / `ctx.mentions` |
| Webhooks | `await Webhook(token).send("Hello!")` |
| Persistent storage | `JsonStore` / `SqliteStore` / `RedisStore` |
| Scheduled tasks | `@bot.cron("0 9 * * *")` |
| Event waiting (typed) | `await bot.wait_for("member_joined", ...)` |
| Collect N events | `await bot.wait_for("reaction_added", count=3)` |
| Plugins (hot-reload) | `await bot.plugins.load(MyPlugin())` |
| Contrib plugins | `pip install nerimity-sdk-contrib` |
| Error handlers | `@bot.on_command_error` |
| Cooldown feedback | automatic "try again in Xs" message |
| Stale cache detection | `user.stale == True` after reconnect |
| Static analysis | `nerimity lint` |
| Debug mode | `Bot(debug=True)` |
| JSON structured logs | `Bot(json_logs=True)` |
| Runtime stats | `bot.stats` — uptime, messages, commands, cache sizes, rate limit hits |
| Auto-restart on crash | enabled by default in `bot.run()` |
| Auto-restart on file save | enabled by default in `bot.run()` |
| Health check endpoint | `Bot(health_port=8080)` → `GET /health` and `GET /stats` |
| Live dev dashboard | `nerimity dev bot.py` with `NERIMITY_HEALTH_PORT` set |
| Built-in /stats command | every bot gets `/stats` automatically |
| DM reply | `await ctx.reply_dm("hi")` |
| Auto-delete reply | `await ctx.reply_then_delete("done", delay=5)` |
| Fetch user by ID | `await bot.rest.fetch_user(user_id)` |
| Bulk role assign | `await bot.rest.add_roles(server_id, user_id, [role1, role2])` |

See the [Getting Started guide](guide/installation.md) or the [Example Bot](example.md) for a full working example.
