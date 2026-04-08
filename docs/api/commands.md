# Commands

## Registering a command

```python
@bot.command(
    "kick",
    description="Kick a member",
    usage="<@member> [reason]",
    category="Moderation",
    aliases=["k"],
    guild_only=True,
    required_user_perms=[Permissions.KICK_MEMBERS],
    cooldown=5.0,
    args=[MemberConverter],
)
async def kick(ctx):
    member = ctx.args[0]
    ...
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | required | Command name |
| `description` | `str` | `""` | Shown in help |
| `usage` | `str` | `""` | Argument hint shown in help |
| `category` | `str` | `"General"` | Groups commands in help output |
| `aliases` | `list[str]` | `[]` | Alternative names |
| `guild_only` | `bool` | `False` | Reject DM invocations |
| `required_user_perms` | `list[Permissions]` | `[]` | User must have all listed perms |
| `cooldown` | `float` | `0` | Per-user cooldown in seconds |
| `args` | `list[converter]` | `[]` | Auto-convert `ctx.args` |
| `middleware` | `list[fn]` | `[]` | Per-command middleware |

## Argument converters

```python
from nerimity_sdk import Int, MemberConverter, UserConverter, ChannelConverter

@bot.command("add", args=[Int, Int])
async def add(ctx):
    a, b = ctx.args   # guaranteed ints

@bot.command("info", args=[MemberConverter])
async def info(ctx):
    member = ctx.args[0]   # Member object
```

Converters accept:
- `Int` — parses to `int`, friendly error on failure
- `MemberConverter` — accepts `[@:id]`, raw ID, or username; resolves from cache
- `UserConverter` — same but returns `User` instead of `Member`
- `ChannelConverter` — resolves channel ID from cache

On failure, a `ConversionError` is raised with a user-facing message and the command is aborted.

## Argument parsing

Raw string parsing before converters run:

```
!cmd hello "quoted string" --flag --count=3
```

- `ctx.args` → `["hello", "quoted string"]`
- `ctx.flags` → `{"flag": True, "count": "3"}`

## Middleware

```python
async def require_admin(ctx, next):
    if not ctx.member or "admin" not in ctx.member.role_ids:
        return await ctx.reply("Admins only.")
    await next(ctx)

# Global (applies to all commands)
bot.router.use(require_admin)

# Per-command
@bot.command("secret", middleware=[require_admin])
async def secret(ctx): ...
```

## Help generator

```python
@bot.command("help")
async def help_cmd(ctx):
    # All categories
    await ctx.reply(bot.router.help_text())

    # One category
    await ctx.reply(bot.router.help_text(category="Moderation"))
```
