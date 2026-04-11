# Security

---

## Protect your token

Your bot token is equivalent to a password. Anyone with it can control your bot and read every message it can see.

- **Never hardcode it** in your source code
- **Never commit it** to Git — add `.env` to `.gitignore` (the scaffold does this automatically)
- **Never share it** in screenshots, streams, or chat
- If it leaks, regenerate it immediately from the developer portal

Always load it from an environment variable:

```python
import os
from dotenv import load_dotenv

load_dotenv()
bot = Bot(token=os.environ["NERIMITY_TOKEN"])
```

---

## Permission checks

Always check permissions before performing mod actions. Use the `requires=` shortcut on commands:

```python
from nerimity_sdk import Permissions

@bot.command("ban", requires=Permissions.BAN_MEMBERS, guild_only=True)
async def ban(ctx):
    ...
```

For manual checks:

```python
@bot.command("nuke", guild_only=True)
async def nuke(ctx):
    if not ctx.member or not ctx.member.has_permission(Permissions.MANAGE_CHANNELS):
        return await ctx.reply("🚫 You don't have permission to do that.")
    ...
```

---

## Validate command input

Never trust user input. Validate and sanitise arguments before using them:

```python
@bot.command("set_limit")
async def set_limit(ctx, amount: int):
    if not 1 <= amount <= 100:
        return await ctx.reply("❌ Amount must be between 1 and 100.")
    ...
```

---

## Restrict sensitive commands

Use `guild_only=True` to prevent commands from being used in DMs where you can't check server roles:

```python
@bot.command("config", guild_only=True, requires=Permissions.MANAGE_SERVER)
async def config(ctx):
    ...
```

---

## Webhook payload validation

If you're using webhooks to receive events from external services, validate the payload signature before acting on it:

```python
import hmac, hashlib

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

Use `hmac.compare_digest` instead of `==` to prevent timing attacks.

---

## Avoid storing sensitive data

Don't store tokens, passwords, or personal user data in `JsonStore` or `SqliteStore` without encryption. For sensitive data, use environment variables or a secrets manager.

---

## Keep dependencies updated

```
pip install --upgrade nerimity-sdk nerimity-sdk-contrib
```

Run this periodically to get security fixes.
