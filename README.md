# nerimity-sdk

A fully-featured Python SDK for building bots on [Nerimity](https://nerimity.com).

```bash
pip install nerimity-sdk
pip install nerimity-sdk-contrib   # optional: ready-made plugins
```

---

## Quickstart

```bash
nerimity create my-bot
cd my-bot && cp .env.example .env   # paste your token
python bot.py
```

Or manually:

```python
import os
from dotenv import load_dotenv
from nerimity_sdk import Bot

load_dotenv()
bot = Bot(token=os.environ["NERIMITY_TOKEN"])

@bot.on("ready")
async def on_ready(me):
    print(f"Logged in as {me.username}#{me.tag}")

@bot.command("ping", description="Replies with Pong!")
async def ping(ctx):
    await ctx.reply("Pong! 🏓")

bot.run()   # auto-restarts on crash and on file save
```

---

## Features

| Feature | How to use |
|---|---|
| Slash + prefix commands | `@bot.command("ping")` — works as `/ping` (default) |
| Type annotation converters | `async def add(ctx, a: int, b: int)` — no `args=` needed |
| Permission shortcut | `@bot.command("ban", requires=Permissions.BAN_MEMBERS)` |
| Command groups | `mod = bot.group("mod")` → `/mod ban`, `/mod kick` |
| Disable/enable commands | `bot.disable_command("ping", server_id)` |
| Buttons | `@bot.button("confirm_{action}")` |
| Confirmation prompts | `await ctx.confirm("Sure?")` |
| Multi-step conversations | `await ctx.ask("Your name?")` |
| Wait for events | `await bot.wait_for("reaction_added", count=3, timeout=60)` |
| Embeds with fields | `Embed().title("Hi").field("Name", "Value")` |
| File uploads | `await ctx.reply_file("image.png")` |
| DM reply | `await ctx.reply_dm("hi")` |
| Auto-delete reply | `await ctx.reply_then_delete("done", delay=5)` |
| Silent reply | `await ctx.reply_silent("shh")` |
| Paginator | `await Paginator(pages).send(ctx)` |
| Auto-paginate long text | `await ctx.reply_paginated(long_text)` |
| Pin/delete messages | `await ctx.pin()` / `await ctx.delete()` |
| Forward message | `await ctx.forward(channel_id)` |
| Persistent storage | `JsonStore` / `SqliteStore` / `RedisStore` |
| Scheduled tasks | `@bot.cron("0 9 * * *")` |
| Plugins (hot-reload) | `await bot.plugins.load(MyPlugin())` |
| Per-guild prefix | `await bot.prefix_resolver.set(server_id, "?")` |
| Cooldown scopes | `cooldown=5.0, cooldown_scope="server"` |
| Rate limit hook | `@bot.on_ratelimit async def handler(route, retry_after)` |
| Health endpoint | `Bot(health_port=8080)` → `GET /health`, `GET /stats` |
| JSON structured logs | `Bot(json_logs=True)` |
| Runtime stats | `bot.stats` — uptime, messages, commands, cache sizes |
| Built-in /stats command | every bot gets `/stats` automatically |
| Auto-restart on crash | enabled by default in `bot.run()` |
| Auto-restart on file save | enabled by default in `bot.run()` |
| REST: bulk role assign | `await bot.rest.add_roles(server_id, user_id, [r1, r2])` |
| REST: create/delete channel | `await bot.rest.create_channel(server_id, name)` |
| REST: fetch bans | `await bot.rest.fetch_bans(server_id)` |
| REST: set nickname | `await bot.rest.set_nickname(server_id, user_id, name)` |
| Webhooks | `await Webhook(token).send("Hello!")` |
| OAuth2 | `OAuth2Client` |

---

## Contrib plugins

```bash
pip install nerimity-sdk-contrib
```

| Plugin | Description |
|---|---|
| `WelcomePlugin` | Greets new members |
| `AutoModPlugin` | Deletes messages matching word/regex list |
| `MessageFilterPlugin` | Block links, invites, or custom patterns |
| `MessageSnapshotPlugin` | Logs deleted/edited messages |
| `ModerationLogPlugin` | Logs mod actions to a channel |
| `WarnPlugin` | `/warn`, `/warnings`, `/clearwarns` with auto-kick |
| `StarboardPlugin` | Reposts highly-reacted messages |
| `LoggingPlugin` | Logs joins, leaves, deletes, edits |
| `RoleMenuPlugin` | React to get a role |
| `ReactionRolesPlugin` | Persistent reaction roles (survives restarts) |
| `AutoRolePlugin` | Auto-assign role on member join |
| `PollPlugin` | Timed reaction poll |
| `GiveawayPlugin` | React-to-enter giveaway |
| `LevelingPlugin` | XP per message, `/level`, `/leaderboard` |
| `BirthdayPlugin` | `/birthday MM-DD`, daily announcements |
| `ReminderPlugin` | `/remind 10m take a break` |
| `AFKPlugin` | `/afk <reason>`, notifies on mention |
| `SuggestionPlugin` | `/suggest <idea>` with reactions |
| `AntiSpamPlugin` | Rate-limit messages, auto-kick/ban |
| `SlowmodePlugin` | Bot-enforced per-channel slowmode |
| `TranslatePlugin` | Auto-translate messages |
| `TicketPlugin` | DM-based support tickets |
| `CounterPlugin` | Live member count in channel name |

---

## CLI

```bash
nerimity create my-bot    # scaffold a new project
nerimity dev bot.py       # dev mode: pretty logs + live dashboard
nerimity lint             # check for common mistakes
nerimity version          # show SDK version
```

---

## Full docs

[https://nerimitysdk.readthedocs.io](https://nerimitysdk.readthedocs.io)

---

Built by [@Lyney:SHOW on Nerimity](https://nerimity.com/app/profile/1750075711936438273) · [JoddabodScripts on GitHub](https://github.com/JoddabodScripts)
