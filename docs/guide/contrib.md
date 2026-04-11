# Contrib Plugins

Official ready-made plugins. Install once, load in your bot.

```
pip install nerimity-sdk-contrib
```

---

## Setup

Load plugins inside your `on_ready` handler:

```python
from nerimity_sdk_contrib import WelcomePlugin, LoggingPlugin, LevelingPlugin

@bot.on("ready")
async def on_ready(me):
    await bot.plugins.load(WelcomePlugin(channel_id="YOUR_CHANNEL_ID"))
    await bot.plugins.load(LoggingPlugin(channel_id="YOUR_LOG_CHANNEL_ID"))
    await bot.plugins.load(LevelingPlugin(announce_channel_id="YOUR_CHANNEL_ID"))
```

---

## Moderation

### `AutoModPlugin`
Deletes messages matching a word or regex list.

```python
await bot.plugins.load(AutoModPlugin(
    blocked=["badword", r"\bspam+\b"],
    log_channel_id="LOG_CHANNEL_ID",
))
```

| Option | Description |
|---|---|
| `blocked` | List of words or regex patterns to block |
| `log_channel_id` | Channel to log deleted messages (optional) |

---

### `AntiSpamPlugin`
Rate-limits messages per user. Auto-kicks, bans, or deletes on threshold.

```python
await bot.plugins.load(AntiSpamPlugin(
    max_messages=5,
    window=5.0,
    action="kick",
    log_channel_id="LOG_CHANNEL_ID",
))
```

| Option | Description |
|---|---|
| `max_messages` | Max messages allowed in `window` seconds |
| `window` | Time window in seconds |
| `action` | `"kick"`, `"ban"`, or `"delete"` |
| `log_channel_id` | Channel to log actions (optional) |

---

### `MessageFilterPlugin`
Block links, invites, or custom regex patterns.

```python
await bot.plugins.load(MessageFilterPlugin(
    block_links=True,
    block_invites=True,
    patterns=[r"discord\.gg"],
    log_channel_id="LOG_CHANNEL_ID",
    exempt_roles=["ROLE_ID"],
))
```

---

### `WarnPlugin`
`/warn @user <reason>` — stores warnings, auto-kicks at threshold.

```python
await bot.plugins.load(WarnPlugin(threshold=3, log_channel_id="LOG_CHANNEL_ID"))
```

Commands: `/warn`, `/warnings`, `/clearwarns`

---

### `SlowmodePlugin`
Bot-enforced per-channel slowmode.

```python
await bot.plugins.load(SlowmodePlugin())
# Then use: /slowmode set <channel_id> <seconds>
```

---

### `ModerationLogPlugin`
Logs mod actions (kicks, bans, role changes) to a channel.

```python
await bot.plugins.load(ModerationLogPlugin(log_channel_id="LOG_CHANNEL_ID"))
```

---

## Logging

### `LoggingPlugin`
Logs joins, leaves, message deletes, and edits.

```python
await bot.plugins.load(LoggingPlugin(channel_id="LOG_CHANNEL_ID"))
```

---

### `MessageSnapshotPlugin`
Logs deleted and edited messages before they're gone.

```python
await bot.plugins.load(MessageSnapshotPlugin(log_channel_id="LOG_CHANNEL_ID"))
```

---

## Welcome & roles

### `WelcomePlugin`
Greets new members with a configurable message.

```python
await bot.plugins.load(WelcomePlugin(
    channel_id="CHANNEL_ID",
    message="👋 Welcome {mention} to the server!",
))
```

Supports `{mention}`, `{username}`, `{tag}` in the message.

---

### `AutoRolePlugin`
Assigns a role automatically when a member joins.

```python
await bot.plugins.load(AutoRolePlugin(server_id="SERVER_ID", role_id="ROLE_ID"))
```

---

### `RoleMenuPlugin`
React to a message to get a role, unreact to remove it.

```python
await bot.plugins.load(RoleMenuPlugin(
    message_id="MESSAGE_ID",
    roles={"👍": "ROLE_ID", "🎮": "GAMER_ROLE_ID"},
))
```

---

### `ReactionRolesPlugin`
Persistent reaction roles that survive restarts.

```python
plugin = ReactionRolesPlugin()
await bot.plugins.load(plugin)
await plugin.add(message_id="MSG_ID", emoji="👍", role_id="ROLE_ID", server_id="SERVER_ID")
```

---

## Engagement

### `LevelingPlugin`
XP per message, level-up announcements, `/level`, `/leaderboard`.

```python
await bot.plugins.load(LevelingPlugin(
    announce_channel_id="CHANNEL_ID",
    xp_per_message=10,
    xp_cooldown=60,
))
```

---

### `StarboardPlugin`
Reposts highly-reacted messages to a starboard channel.

```python
await bot.plugins.load(StarboardPlugin(
    channel_id="STARBOARD_CHANNEL_ID",
    emoji="⭐",
    threshold=3,
))
```

---

### `GiveawayPlugin`
React-to-enter giveaway with a random winner.

```python
plugin = GiveawayPlugin()
await bot.plugins.load(plugin)

@bot.command("giveaway")
async def giveaway(ctx):
    await plugin.start(ctx, prize="Nitro", duration=3600, emoji="🎉")
```

---

### `PollPlugin`
Timed reaction poll with automatic result tallying.

```python
plugin = PollPlugin()
await bot.plugins.load(plugin)

@bot.command("poll")
async def poll(ctx):
    await plugin.create(ctx, question="Best colour?", options=["🔴 Red","🔵 Blue"], duration=300)
```

---

### `SuggestionPlugin`
`/suggest <idea>` — posts to a suggestions channel with 👍/👎 reactions.

```python
await bot.plugins.load(SuggestionPlugin(channel_id="SUGGESTIONS_CHANNEL_ID"))
```

---

## Utility

### `ReminderPlugin`
`/remind 10m take a break` — DMs the user after the time.

```python
plugin = ReminderPlugin()
await bot.plugins.load(plugin)
```

---

### `AFKPlugin`
`/afk <reason>` — bot replies to mentions with the AFK message.

```python
await bot.plugins.load(AFKPlugin())
```

---

### `BirthdayPlugin`
`/birthday MM-DD` — announces birthdays daily.

```python
await bot.plugins.load(BirthdayPlugin(
    announce_channel_id="CHANNEL_ID",
    message="🎂 Happy birthday {mention}!",
))
```

---

### `TranslatePlugin`
Auto-translates messages in a channel. No API key needed (uses MyMemory).

```python
await bot.plugins.load(TranslatePlugin(
    watch_channel_id="CHANNEL_ID",
    target_lang="en",
))
```

---

### `TicketPlugin`
DM-based support tickets — users DM the bot, staff reply via a channel.

```python
await bot.plugins.load(TicketPlugin(
    staff_channel_id="STAFF_CHANNEL_ID",
    open_message="Your ticket has been opened. Staff will reply shortly.",
    close_message="Your ticket has been closed.",
))
```

---

### `CounterPlugin`
Keeps a channel name updated with a live count.

```python
await bot.plugins.load(CounterPlugin(
    server_id="SERVER_ID",
    channel_id="CHANNEL_ID",
    label="Members: {count}",
    interval=300,
    count_fn=lambda bot: len(bot.cache.get_members("SERVER_ID")),
))
```
