# Example Bot

A complete bot demonstrating every major feature. Source: [`example_bot/bot.py`](https://github.com/JoddabodScripts/Nerimity-SDK/blob/master/example_bot/bot.py)

## Setup

```bash
pip install "nerimity-sdk[cron]"
export NERIMITY_TOKEN=your_token_here
export ANNOUNCE_CHANNEL=your_channel_id   # optional, for cron demo
python example_bot/bot.py
```

## What it demonstrates

### Prefix commands with converters

```python
from nerimity_sdk import Int, MemberConverter

@bot.command("add", args=[Int, Int])
async def add(ctx):
    a, b = ctx.args   # already ints
    await ctx.reply(f"{a} + {b} = {a + b}")

@bot.command("kick", args=[MemberConverter], guild_only=True)
async def kick(ctx):
    member = ctx.args[0]
    if not await ctx.confirm(f"Kick {member.user.username}?"):
        return await ctx.reply("Cancelled.")
    await ctx.rest.kick_member(ctx.server_id, member.user.id)
    await ctx.reply(f"Kicked {mention(member.user.id)}")
```

### Slash command

```python
@bot.command("info", description="Show bot info")
async def slash_info(ctx):
    from nerimity_sdk import __version__
    await ctx.reply(f"nerimity-sdk v{__version__}")
```

### Poll with buttons

```python
from nerimity_sdk import Button

@bot.command("poll", description="Start a yes/no poll")
async def poll(ctx):
    question = " ".join(ctx.args) if ctx.args else "Do you agree?"
    msg = await ctx.reply(
        f"📊 **{question}**",
        buttons=[
            Button(id=f"poll_yes_{ctx.channel_id}", label="👍 Yes"),
            Button(id=f"poll_no_{ctx.channel_id}",  label="👎 No", alert=True),
        ]
    )

@bot.button("poll_yes_{channel_id}")
async def on_poll_yes(bctx):
    await bctx.popup("Vote recorded!", "You voted 👍 Yes")

@bot.button("poll_no_{channel_id}")
async def on_poll_no(bctx):
    await bctx.popup("Vote recorded!", "You voted 👎 No")
```

### Paginator

```python
@bot.command("help")
async def help_cmd(ctx):
    pages = bot.router.help_text().split("\n\n")
    await Paginator(pages).send(ctx)
```

### Scheduled task

```python
@bot.cron("0 9 * * 1")   # Every Monday 09:00 UTC
async def weekly():
    await bot.rest.create_message(ANNOUNCE_CHANNEL, "Good morning!")
```

### Persistent storage

```python
@bot.command("setprefix")
async def setprefix(ctx):
    await bot.store.set(f"guild:{ctx.server_id}:prefix", ctx.args[0])
    await ctx.reply(f"Prefix set to `{ctx.args[0]}`")
```

### Global error handlers

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

### Plugin

```python
from nerimity_sdk import PluginBase, listener

class WelcomePlugin(PluginBase):
    name = "welcome"

    @listener("server:member_joined")
    async def on_join(self, event):
        await self.bot.rest.create_message(
            channel_id, f"Welcome {mention(event.member.user.id)}!"
        )

async def main():
    await bot.plugins.load(WelcomePlugin())
    bot.run()
```

## Full source

See [`example_bot/bot.py`](https://github.com/JoddabodScripts/Nerimity-SDK/blob/master/example_bot/bot.py) for the complete runnable file.
