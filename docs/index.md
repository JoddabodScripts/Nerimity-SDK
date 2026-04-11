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

Open **Command Prompt** and run:

```
pip install nerimity-sdk
nerimity create my-bot
cd my-bot
copy .env.example .env
```

Open `.env` in Notepad — run this in Command Prompt (`.env` is hidden in File Explorer, so open it this way):

```
notepad .env
```

Paste your token:

```
NERIMITY_TOKEN=paste_your_token_here
```

Then start your bot:

```
python bot.py
```

Or set it up manually — create `bot.py`:

```python
import os
from dotenv import load_dotenv
from nerimity_sdk import Bot

load_dotenv()
bot = Bot(token=os.environ["NERIMITY_TOKEN"])

@bot.on("ready")
async def on_ready(me):
    print(f"✅ Logged in as {me.username}!")

@bot.command("ping", description="Replies with Pong!")
async def ping(ctx):
    await ctx.reply("Pong! 🏓")

bot.run()
```

And a `.env` file in the same folder:

```
NERIMITY_TOKEN=paste_your_token_here
```

> **Linux:** use `cp .env.example .env` instead of `copy`.

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
| Create role | `await bot.rest.create_role(server_id, name, hex_color, permissions)` |
| Fetch all members | `await bot.rest.fetch_server_members(server_id)` |
| Forward message | `await ctx.forward(channel_id)` |
| Rest of args as string | `ctx.rest_text` |
| Float/bool converters | `async def cmd(ctx, ratio: float, silent: bool)` |
| Command groups | `@bot.group("mod")` → `/mod ban`, `/mod kick` |
| Disable/enable commands | `bot.disable_command("ping")` / `bot.enable_command("ping", server_id)` |
| Delete triggering message | `await ctx.delete()` |
| Paginate long replies | `await ctx.reply_paginated(long_text)` |
| Set nickname | `await bot.rest.set_nickname(server_id, user_id, nickname)` |
| Fetch bans | `await bot.rest.fetch_bans(server_id)` |
| Create/delete channel | `await bot.rest.create_channel(server_id, name)` / `delete_channel(id)` |
| Cooldown scope | `@bot.command("x", cooldown=5.0, cooldown_scope="server")` |
| Alias slash sync | aliases are now synced to the slash menu automatically |
| Partial wait_for results | `wait_for(count=3)` returns collected events on timeout instead of raising |
| Rate limit hook | `@bot.on_ratelimit async def handler(route, retry_after)` |
| Embed fields | `Embed().field("Name", "Value", inline=True)` |
| Raw dict embed | `await ctx.reply_embed({"title": "hi"})` |
| Fetch message by ID | `await bot.rest.fetch_message(channel_id, message_id)` |
| Fetch server from API | `await bot.rest.fetch_server(server_id)` |
| ctx.ensure_member() | API fallback for the command author's member object |
| Request timeout | `bot.rest.timeout = 30.0` (default) |
| Disable built-in /stats | `Bot(disable_builtin_stats=True)` |
| Edit message with buttons | `await ctx.edit(msg.id, "new content", buttons=[...])` |
| Silent reply | `await ctx.reply_silent("shh")` |
| Fetch channel from API | `await bot.rest.fetch_channel(channel_id)` |

See the [Getting Started guide](guide/installation.md) or the [Example Bot](example.md) for a full working example.

---

Built by [@Kansane:TETO on Nerimity](https://nerimity.com/app/profile/1750075711936438273) · [JoddabodScripts on GitHub](https://github.com/JoddabodScripts)