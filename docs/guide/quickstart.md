# Quick Start

## Minimal bot

```python
from nerimity_sdk import Bot

bot = Bot(token="YOUR_TOKEN", prefix="!")

@bot.on("ready")
async def on_ready(me):
    print(f"Logged in as {me.username}#{me.tag}")

@bot.command("ping", description="Pong!")
async def ping(ctx):
    await ctx.reply("Pong! 🏓")

bot.run()
```

## Adding a slash command

```python
@bot.slash("info", description="Show bot info")
async def slash_info(sctx):
    from nerimity_sdk import __version__
    await sctx.reply(f"nerimity-sdk v{__version__}")
```

## Argument converters

```python
from nerimity_sdk import Int, MemberConverter

@bot.command("add", args=[Int, Int])
async def add(ctx):
    a, b = ctx.args   # already ints
    await ctx.reply(f"{a + b}")

@bot.command("kick", args=[MemberConverter], guild_only=True)
async def kick(ctx):
    member = ctx.args[0]
    if not await ctx.confirm(f"Kick {member.user.username}?"):
        return await ctx.reply("Cancelled.")
    await ctx.rest.kick_member(ctx.server_id, member.user.id)
    await ctx.reply("Done.")
```

## Buttons

```python
from nerimity_sdk import Button, ComponentRow

@bot.command("poll")
async def poll(ctx):
    msg = await ctx.reply("Vote!")

    @bot.button(f"vote:yes:{msg.id}", ttl=300)
    async def on_yes(bctx):
        await bctx.reply("You voted Yes!")

    @bot.button(f"vote:no:{msg.id}", ttl=300)
    async def on_no(bctx):
        await bctx.reply("You voted No!")
```

## Paginator

```python
from nerimity_sdk import Paginator

@bot.command("list")
async def list_cmd(ctx):
    pages = ["Page 1: ...", "Page 2: ...", "Page 3: ..."]
    await Paginator(pages).send(ctx)
```

## Error handling

```python
@bot.on_command_error
async def on_error(ctx, error):
    await ctx.reply(f"❌ {error}")

@bot.on_slash_error
async def on_slash_error(sctx, error):
    await sctx.reply(f"❌ {error}")
```

## Scheduled tasks

```python
@bot.cron("0 9 * * 1")   # Every Monday 09:00 UTC
async def weekly():
    await bot.rest.create_message(CHANNEL_ID, "Good morning!")
```

## Persistent storage

```python
from nerimity_sdk import JsonStore

bot = Bot(token="...", store=JsonStore("data.json"))

@bot.command("setprefix")
async def setprefix(ctx):
    await bot.store.set(f"guild:{ctx.server_id}:prefix", ctx.args[0])
    await ctx.reply(f"Prefix set to `{ctx.args[0]}`")
```
