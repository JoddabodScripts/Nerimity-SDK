# Context

Passed to every prefix command handler. Wraps the triggering message with convenience helpers.

## Properties

| Property | Type | Description |
|---|---|---|
| `ctx.message` | `Message` | The raw message object |
| `ctx.author` | `User` | Message author |
| `ctx.channel_id` | `str` | Channel snowflake ID |
| `ctx.server_id` | `str \| None` | Server ID (None in DMs) |
| `ctx.server` | `Server \| None` | Server from cache |
| `ctx.channel` | `Channel \| None` | Channel from cache |
| `ctx.member` | `Member \| None` | Author's server member from cache |
| `ctx.args` | `list` | Parsed positional arguments (converted if `args=` set) |
| `ctx.flags` | `dict` | Named flags (`--flag=value`) |
| `ctx.mentions` | `list[User]` | Resolved `[@:id]` mentions from message content |

## Methods

### `await ctx.reply(content)`
Send a message to the same channel. Returns `Message`.

### `await ctx.react(emoji, emoji_id=None, gif=False, webp=False)`
Add a reaction to the triggering message.

```python
await ctx.react("👍")                          # unicode
await ctx.react("wave", emoji_id="123456")    # custom emoji
```

### `await ctx.unreact(emoji, emoji_id=None)`
Remove a reaction.

### `await ctx.ask(prompt, timeout=30.0, check=None)`
Send a prompt and wait for the author's next message in the same channel.
Returns `Message` or `None` on timeout.

```python
name = await ctx.ask("What's your name?", timeout=30)
if name:
    await ctx.reply(f"Hi {name.content}!")
```

### `await ctx.confirm(prompt, timeout=30.0)`
Ask a yes/no question. Returns `True`, `False`, or `None` on timeout.

```python
if not await ctx.confirm("Are you sure?"):
    return await ctx.reply("Cancelled.")
```

Accepts: `yes`, `y`, `yeah`, `yep`, `confirm`, `ok` → `True`  
Accepts: `no`, `n`, `nope`, `cancel`, `abort` → `False`

### `await ctx.fetch_messages(limit=50, before=None, after=None)`
Fetch messages from the channel. Returns `list[Message]`.

### `await ctx.fetch_member(user_id)`
Look up a member from cache. Returns `Member | None`.

### `await ctx.send_typing()`
Send a typing indicator to the channel.
