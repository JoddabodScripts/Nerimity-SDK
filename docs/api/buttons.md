# Buttons

## Building buttons

```python
from nerimity_sdk import Button, ComponentRow

row = ComponentRow()
row.add(Button(id="confirm:delete:123", label="✅ Confirm"))
row.add(Button(id="cancel:delete:123",  label="❌ Cancel", alert=True))
```

## Registering handlers

Use `{name}` segments in patterns to capture dynamic parts:

```python
@bot.button("confirm:{action}:{target}")
async def on_confirm(bctx):
    action = bctx.params["action"]   # e.g. "delete"
    target = bctx.params["target"]   # e.g. "123"
    await bctx.reply(f"Confirmed: {action} on {target}")
```

Wildcard patterns also work:

```python
@bot.button("poll:yes:*")
async def on_yes(bctx): ...
```

### TTL (time-to-live)

Registrations expire after `ttl` seconds. Old buttons stop responding cleanly:

```python
@bot.button("vote:*", ttl=300)   # expires after 5 minutes
async def on_vote(bctx): ...
```

## ButtonContext

| Property | Type | Description |
|---|---|---|
| `bctx.button_id` | `str` | Full button ID |
| `bctx.message_id` | `str` | Message containing the button |
| `bctx.channel_id` | `str` | Channel ID |
| `bctx.server_id` | `str \| None` | Server ID |
| `bctx.user_id` | `str` | User who clicked |
| `bctx.user` | `User \| None` | Resolved from cache |
| `bctx.params` | `dict[str, str]` | Captured pattern segments |

### `await bctx.reply(content)`
Send a message to the channel.

### `await bctx.update_message(content)`
Edit the message that contains the button.

### `await bctx.defer()`
Acknowledge the click silently (no-op placeholder for API parity).

## Error handling

```python
@bot.on_button_error
async def on_button_error(bctx, error):
    await bctx.reply(f"❌ {error}")
```
