# Slash Commands

Nerimity slash commands are registered with the API and dispatched when a user types `/command`.

## Registering

```python
@bot.slash("ban", description="Ban a user", args_hint="<user_id> [reason]")
async def ban(sctx):
    parts = sctx.args.split(None, 1)
    user_id = parts[0]
    await sctx.rest.ban_member(sctx.server_id, user_id)
    await sctx.reply(f"Banned {mention(user_id)}")
```

Slash commands are automatically synced to Nerimity on bot ready via `POST /api/applications/bot/commands`.

## SlashContext

| Property | Type | Description |
|---|---|---|
| `sctx.command_name` | `str` | The slash command name |
| `sctx.args` | `str` | Raw argument string |
| `sctx.channel_id` | `str` | Channel ID |
| `sctx.server_id` | `str \| None` | Server ID |
| `sctx.user_id` | `str` | Invoking user ID |
| `sctx.user` | `User \| None` | Resolved from cache |
| `sctx.server` | `Server \| None` | Resolved from cache |

### `await sctx.reply(content)`
Send a response to the slash command.

## Error handling

```python
@bot.on_slash_error
async def on_slash_error(sctx, error):
    await sctx.reply(f"❌ {error}")
```
