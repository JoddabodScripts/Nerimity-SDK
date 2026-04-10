# Quick Start

This guide walks you from zero to a working bot in 5 minutes.

## 1. Get a token

Go to [nerimity.com/app/settings/developer/applications](https://nerimity.com/app/settings/developer/applications).

1. Click **New Application**
2. Go to the **Bot** tab and click **Add Bot**
3. Copy the token

## 2. Create a project

```bash
nerimity create my-bot
cd my-bot
cp .env.example .env
```

Open `.env` and paste your token:

```
NERIMITY_TOKEN=paste_your_token_here
```

## 3. Run it

```bash
python bot.py
```

You should see `Logged in as YourBot#0000` in the terminal.

---

## 4. Add your first command

Open `bot.py`. Add this anywhere before `bot.run()`:

```python
@bot.command("hello", description="Say hello back")
async def hello(ctx):
    await ctx.reply(f"Hello, {ctx.author.username}!")
```

Save the file — the bot restarts automatically. Type `/hello` in any channel the bot can see.

---

## 5. Read arguments

```python
@bot.command("say", description="Repeat something")
async def say(ctx):
    if not ctx.args:
        return await ctx.reply("Usage: /say <message>")
    await ctx.reply(" ".join(ctx.args))
```

Type `/say hello world` → bot replies `hello world`.

---

## 6. Use typed converters

**Option A — type annotations** (simplest):

```python
@bot.command("double", description="Double a number")
async def double(ctx, n: int):
    await ctx.reply(str(n * 2))
```

**Option B — explicit `args=`**:

```python
from nerimity_sdk import Int

@bot.command("double", description="Double a number", args=[Int])
async def double(ctx):
    n = ctx.args[0]
    await ctx.reply(str(n * 2))
```

Either way, if the user types `/double abc` they get a friendly error automatically.

---

## 7. Handle errors

Add this once and all command errors show a message instead of silently failing:

```python
@bot.on_command_error
async def on_error(ctx, error):
    await ctx.reply(f"❌ {error}")
```

---

## 8. Slash commands work automatically

Every `@bot.command` is already a slash command — it shows up in Nerimity's `/` menu automatically. The default prefix is `/` so users just type `/ping`.

```python
@bot.command("ping", description="Check if the bot is alive")
async def ping(ctx):
    await ctx.reply("Pong!")
# Users type /ping
```

To keep a command prefix-only (hidden from the `/` menu):

```python
@bot.command_private("debug")
async def debug(ctx):
    await ctx.reply("secret")
```

---

## 9. Save data between restarts

```python
from nerimity_sdk import JsonStore

bot = Bot(token=os.environ["NERIMITY_TOKEN"], prefix="!", store=JsonStore("data.json"))

@bot.command("remember", description="Remember a value")
async def remember(ctx):
    if not ctx.args:
        return await ctx.reply("Usage: !remember <value>")
    await bot.store.set(f"user:{ctx.author.id}:note", ctx.args[0])
    await ctx.reply(f"Remembered: {ctx.args[0]}")

@bot.command("recall", description="Recall your saved value")
async def recall(ctx):
    note = await bot.store.get(f"user:{ctx.author.id}:note")
    await ctx.reply(note or "Nothing saved yet.")
```

---

## What's next?

- [Commands in depth](../api/commands.md) — converters, middleware, permissions, help generator
- [Slash commands](../api/slash.md) — `/` commands with argument types
- [Buttons](../api/buttons.md) — interactive button handlers
- [Plugins](../api/plugins.md) — split your bot into reloadable modules
- [Example Bot](../example.md) — a complete bot showing everything at once

## Testing

Use `MockBot` to unit test without a real connection:

```python
from nerimity_sdk.testing import MockBot

bot = MockBot(prefix="/")

@bot.command("ping")
async def ping(ctx):
    await ctx.reply("Pong!")

await bot.simulate_message("/ping")           # simulate a prefix/slash message
await bot.simulate_slash("ping")              # simulate a slash command directly
await bot.simulate_event("server:member_joined", {...})  # simulate any gateway event
```
