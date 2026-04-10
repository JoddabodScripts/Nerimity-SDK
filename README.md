# nerimity-sdk

A Python library for building bots on [Nerimity](https://nerimity.com).

```bash
pip install nerimity-sdk
```

---

## How it works

You create a `Bot`, attach handlers to it with decorators, then call `bot.run()`.
The bot connects to Nerimity over a WebSocket, receives events, and dispatches them to your handlers.

```
Nerimity server
      │
      │  WebSocket (Socket.IO)
      ▼
  GatewayClient          ← receives raw events, puts them in a queue
      │
      ▼
  EventEmitter           ← deserializes events into typed objects, calls your handlers
      │
      ├── @bot.on("message:created")   ← your event listeners
      ├── @bot.command("ping")         ← prefix commands  (!ping)
      ├── @bot.slash("info")           ← slash commands   (/info)
      └── @bot.button("confirm:*")     ← button clicks
```

Everything your handlers need is in the `ctx` (Context) object passed to them.

---

## Quickstart

**1. Get a bot token**

Go to [nerimity.com/app/settings/developer/applications](https://nerimity.com/app/settings/developer/applications), create an application, add a Bot, and copy the token.

**2. Scaffold a project**

```bash
nerimity create my-bot
cd my-bot
cp .env.example .env   # paste your token in here
python bot.py
```

**3. Or start from scratch**

```python
# bot.py
import os
from dotenv import load_dotenv
from nerimity_sdk import Bot

load_dotenv()
bot = Bot(token=os.environ["NERIMITY_TOKEN"], prefix="!")

@bot.on("ready")
async def on_ready(me):
    print(f"Logged in as {me.username}#{me.tag}")

@bot.command("ping", description="Replies with Pong!")
async def ping(ctx):
    await ctx.reply("Pong! 🏓")

bot.run()
```

---

## Core concepts

### The Bot object

```python
bot = Bot(
    token=os.environ["NERIMITY_TOKEN"],
    prefix="!",          # prefix for commands like !ping
)
```

`bot.run()` is blocking — it connects and stays connected until you Ctrl+C.

---

### Event listeners

Listen to anything happening on Nerimity:

```python
@bot.on("message:created")
async def on_message(event):
    # event is a typed MessageCreatedEvent — not a raw dict
    print(event.message.content)

@bot.on("server:member_joined")
async def on_join(event):
    print(f"{event.member.user.username} joined {event.server_id}")

@bot.on("*")  # wildcard — fires for every event
async def log_everything(event):
    print(event)
```

Every event is a typed dataclass — you get autocomplete, not `event["data"]["user"]["id"]` chains.

---

### Prefix commands

Commands triggered by a message starting with your prefix (e.g. `!ping`):

```python
@bot.command("ping", description="Replies with Pong!")
async def ping(ctx):
    await ctx.reply("Pong!")
```

**With argument converters** — `ctx.args` are already the right types:

```python
from nerimity_sdk import Int, MemberConverter

@bot.command("add", description="Add two numbers", args=[Int, Int])
async def add(ctx):
    a, b = ctx.args   # guaranteed ints, friendly error if user types garbage
    await ctx.reply(f"{a} + {b} = {a + b}")

@bot.command("kick", args=[MemberConverter], guild_only=True)
async def kick(ctx):
    member = ctx.args[0]   # a Member object, not a raw string
    if not await ctx.confirm(f"Kick {member.user.username}?"):
        return await ctx.reply("Cancelled.")
    await ctx.rest.kick_member(ctx.server_id, member.user.id)
    await ctx.reply("Done.")
```

---

### The Context object (`ctx`)

Every command handler receives a `ctx` with everything you need:

```python
ctx.author          # User who sent the message
ctx.server          # Server it was sent in (None in DMs)
ctx.channel_id      # Where to reply
ctx.args            # Parsed arguments
ctx.flags           # --flag=value flags
ctx.mentions        # [@:id] mentions resolved to User objects

await ctx.reply("hello")                    # send a message
await ctx.react("👍")                       # react to the message
await ctx.ask("What's your name?")          # wait for a follow-up
await ctx.confirm("Are you sure?")          # yes/no prompt → True/False/None
await ctx.author.send(bot.rest, "Hi!")      # send a DM
```

---

### Slash commands

Every `@bot.command` is automatically a slash command — it registers with Nerimity's API and shows in the `/` menu. No separate handler needed.

```python
@bot.command("ban", description="Ban a user")
async def ban(ctx):
    # works as !ban AND /ban
    ...
```

To keep a command prefix-only (not in the `/` menu):

```python
@bot.command_private("debug")
async def debug(ctx):
    await ctx.reply("secret")
```

`@bot.slash` is just an alias for `@bot.command`.

---

### Buttons

```python
from nerimity_sdk import Button

@bot.command("confirm", description="Confirm an action")
async def confirm_cmd(ctx):
    await ctx.reply(
        "Are you sure?",
        buttons=[
            Button(id="yes_confirm", label="✅ Yes"),
            Button(id="no_confirm",  label="❌ No", alert=True),
        ]
    )

@bot.button("yes_{action}")
async def on_yes(bctx):
    await bctx.popup("Done!", f"Confirmed: {bctx.params['action']}")

@bot.button("no_{action}")
async def on_no(bctx):
    await bctx.popup("Cancelled", "Nothing was changed.")
```

> Button IDs cannot contain colons. Use underscores as separators.

---

### Error handling

Without error handlers, errors are logged but don't crash the bot.
With them, you can send a friendly message to the user:

```python
@bot.on_command_error
async def on_error(ctx, error):
    await ctx.reply(f"❌ {error}")

@bot.on_slash_error
async def on_slash_error(sctx, error):
    await sctx.reply(f"❌ {error}")

@bot.on_button_error
async def on_button_error(bctx, error):
    await bctx.reply(f"❌ {error}")
```

---

### Plugins

Split your bot into reloadable modules:

```python
# plugins/welcome.py
from nerimity_sdk import PluginBase, listener, mention

class WelcomePlugin(PluginBase):
    name = "welcome"

    @listener("server:member_joined")
    async def on_join(self, event):
        await self.bot.rest.create_message(
            "YOUR_CHANNEL_ID",
            f"👋 Welcome {mention(event.member.user.id)}!"
        )

async def setup(bot):
    await bot.plugins.load(WelcomePlugin())
```

Load it:

```python
await bot.plugins.load_from_path("plugins/welcome.py")

# Hot-reload without restarting:
await bot.plugins.reload("welcome")
```

---

### Persistent storage

Save data between restarts:

```python
from nerimity_sdk import JsonStore

bot = Bot(token=..., store=JsonStore("data.json"))

# In any command:
await bot.store.set(f"guild:{ctx.server_id}:prefix", "?")
prefix = await bot.store.get(f"guild:{ctx.server_id}:prefix") or "!"
```

Swap `JsonStore` for `SqliteStore` or `RedisStore` with no other code changes.

---

### Scheduled tasks

```python
@bot.cron("0 9 * * 1")   # every Monday at 09:00 UTC
async def weekly():
    await bot.rest.create_message("CHANNEL_ID", "Good morning!")
```

Requires `pip install "nerimity-sdk[cron]"`.

---

### Waiting for events

```python
# Wait for a specific member to join
event = await bot.wait_for(
    "server:member_joined",
    check=lambda e: e.member.user.id == "12345",
    timeout=60,
)
```

---

### Paginator

For long responses like help menus or leaderboards:

```python
from nerimity_sdk import Paginator

@bot.command("help")
async def help_cmd(ctx):
    pages = bot.router.help_text().split("\n\n")
    await Paginator(pages).send(ctx)
```

---

### Mention helpers

```python
from nerimity_sdk import mention

mention("123456")          # → "[@:123456]"  (use in messages to ping someone)
ctx.mentions               # list of User objects mentioned in the command message
```

---

## CLI tools

```bash
nerimity create my-bot    # scaffold a new project
nerimity version          # show SDK version
nerimity lint             # check your bot code for common mistakes
nerimity-help             # quick reference in your terminal
```

---

## Optional extras

```bash
pip install "nerimity-sdk[cron]"     # @bot.cron() scheduled tasks
pip install "nerimity-sdk[watch]"    # watch=True auto-reload plugins on save
pip install "nerimity-sdk[sqlite]"   # SqliteStore
pip install "nerimity-sdk[redis]"    # RedisStore
```

---

## Full docs

[https://nerimitysdk.readthedocs.io/en/latest/](https://nerimitysdk.readthedocs.io/en/latest/)
---

Built by [@Lyney:SHOW on Nerimity](https://nerimity.com/app/profile/1750075711936438273) · [JoddabodScripts on GitHub](https://github.com/JoddabodScripts)
