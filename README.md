# nerimity-sdk

A fully-featured Python SDK for building [Nerimity](https://nerimity.com) bots. Think discord.py, but for Nerimity.

## Install

```bash
pip install nerimity-sdk
```

With Redis support for multi-process bots:
```bash
pip install "nerimity-sdk[redis]"
```

## Quickstart

```bash
nerimity create my-bot
cd my-bot
# edit bot.py and set your token
python bot.py
```

Or manually:

```python
from nerimity_sdk import Bot

bot = Bot(token="YOUR_TOKEN", prefix="!")

@bot.on("ready")
async def on_ready(me):
    print(f"Logged in as {me.username}#{me.tag}")

@bot.command("ping", description="Replies with Pong!")
async def ping(ctx):
    await ctx.reply("Pong!")

bot.run()
```

## Features

### Core Transport
- Socket.IO gateway with **auto-reconnect** and **exponential backoff**
- **Event queue** so gateway bursts never drop events
- HTTP REST client with **per-route rate limit buckets** and `retry-after` handling

### Event System
```python
# Standard listener
@bot.on("message:created")
async def on_message(data): ...

# One-shot
@bot.once("ready")
async def on_first_ready(me): ...

# Wildcard — fires for every event
@bot.on("*")
async def log_all(data): ...
```

Every handler runs in async isolation — one crashing handler won't affect others.

### Commands
```python
@bot.command(
    "ban",
    description="Ban a user",
    usage="<user_id>",
    category="Moderation",
    guild_only=True,
    required_user_perms=[Permissions.BAN_MEMBERS],
    cooldown=5.0,
)
async def ban(ctx):
    user_id = ctx.args[0]
    await ctx.rest.ban_member(ctx.server_id, user_id)
    await ctx.reply(f"Banned {user_id}")
```

Flags: `!cmd --silent --count=3 "quoted arg"` → `ctx.flags["silent"]`, `ctx.args[0]`

### Middleware
```python
async def log_middleware(ctx, next):
    print(f"Command from {ctx.author.username}")
    await next(ctx)

bot.router.use(log_middleware)
```

### Context Object
```python
ctx.message        # Message object
ctx.author         # User
ctx.channel_id     # str
ctx.server         # Server | None (from cache)
ctx.member         # Member | None (from cache)
ctx.args           # list[str]
ctx.flags          # dict[str, Any]

await ctx.reply("hello")
await ctx.fetch_messages(limit=10)
await ctx.fetch_member(user_id)
```

### Cache
Automatic LRU/TTL cache for servers, channels, members, users, and messages. Partial gateway updates are merged intelligently — no stale overwrites.

```python
server = bot.cache.servers.get("server_id")
user   = bot.cache.users.get("user_id")
```

### Permissions
```python
from nerimity_sdk import has_permission, Permissions

if has_permission(member, server, Permissions.KICK_MEMBERS):
    ...
```

### Plugins
```python
from nerimity_sdk import PluginBase, listener

class ModerationPlugin(PluginBase):
    name = "moderation"

    @listener("server:member_joined")
    async def on_join(self, data):
        print("Member joined:", data)

    async def on_ready(self):
        print("Moderation plugin ready!")

async def setup(bot):
    await bot.plugins.load(ModerationPlugin())
```

Hot reload at runtime:
```python
await bot.plugins.reload("moderation")
```

### Debug Mode
```python
bot = Bot(token="...", debug=True)
# Logs all raw gateway payloads with pretty JSON formatting
```

### Testing
```python
from nerimity_sdk.testing import MockBot

bot = MockBot(prefix="!")

@bot.command("ping")
async def ping(ctx):
    await ctx.reply("Pong!")

# In your test:
async def test_ping():
    await bot.simulate_message("!ping")
    bot.rest.create_message.assert_called_once()
```

### Sharding (stub)
```python
# Architecture is shard-ready. When Nerimity adds sharding:
bot = Bot.from_shard(token="...", shard_id=0, shard_count=4)
```

## Project Structure

```
nerimity_sdk/
├── bot.py                  # Main Bot class
├── models.py               # Typed data models
├── testing.py              # MockBot + test helpers
├── transport/
│   ├── gateway.py          # Socket.IO client
│   └── rest.py             # HTTP REST client
├── events/
│   └── emitter.py          # Async event emitter
├── commands/
│   └── router.py           # Prefix command router
├── cache/
│   ├── store.py            # LRU/TTL cache
│   └── redis_adapter.py    # Optional Redis adapter
├── context/
│   └── ctx.py              # Context object
├── permissions/
│   └── checker.py          # Permission helpers
├── plugins/
│   └── manager.py          # Plugin system
├── cli/
│   └── main.py             # nerimity CLI
└── utils/
    └── logging.py          # Structured logging
```

## License

MIT
