# Plugin Marketplace

Community plugins for nerimity-sdk. To add yours, open a PR to the docs repo.

## Official contrib plugins

```bash
pip install nerimity-sdk-contrib
```

```python
# Replace [name of plugin] with the plugins you want to use, e.g. WelcomePlugin, LoggingPlugin
from nerimity_sdk_contrib import [name of plugin], [name of plugin]

@bot.on("ready")
async def on_ready(me):
    await bot.plugins.load(WelcomePlugin(channel_id="123"))
    await bot.plugins.load(AutoModPlugin(blocked=["badword"], log_channel_id="456"))
    await bot.plugins.load(StarboardPlugin(channel_id="789", threshold=3))
    await bot.plugins.load(LoggingPlugin(channel_id="000"))
```

### Available plugins

| Plugin | Description | Options |
|---|---|---|
| `WelcomePlugin` | Greets new members | `channel_id`, `message` (supports `{mention}`, `{username}`, `{tag}`) |
| `AutoModPlugin` | Deletes messages matching a word/regex list | `blocked`, `log_channel_id` |
| `StarboardPlugin` | Reposts highly-reacted messages to a starboard channel | `channel_id`, `emoji`, `threshold` |
| `LoggingPlugin` | Logs joins, leaves, deletes, and edits | `channel_id` |
| `RoleMenuPlugin` | React to a message to get a role, unreact to remove it | `message_id`, `roles` (dict of emoji → role_id) |
| `PollPlugin` | Timed reaction poll with automatic result tallying | loaded once, then `await plugin.create(ctx, question, options, duration)` |
| `AntiSpamPlugin` | Rate-limits messages per user, auto-kicks/bans/deletes on threshold | `max_messages`, `window`, `action` (`"kick"`, `"ban"`, `"delete"`), `log_channel_id` |
| `LevelingPlugin` | XP per message with cooldown, level-up announcements, persistent storage | `announce_channel_id`, `xp_per_message`, `xp_cooldown` |
| `TicketPlugin` | DM-based support tickets — users DM the bot, staff reply via a channel | `staff_channel_id`, `open_message`, `close_message` |
| `GiveawayPlugin` | React-to-enter giveaway with random winner after a duration | loaded once, then `await plugin.start(ctx, prize, duration, emoji)` |
| `ReminderPlugin` | `!remind 10m take a break` — DMs the user after the time | loaded once, then `await plugin.set(ctx)` |
| `TranslatePlugin` | Auto-translate messages in a channel (MyMemory, no API key needed) | `watch_channel_id`, `target_lang` |

---

## Community plugins

*None listed yet — be the first!*

To list your plugin here, open a PR adding a row to this table:

| Plugin | Author | Description | Install |
|---|---|---|---|
| your-plugin | @you | What it does | `pip install your-plugin` |

---

## Writing a plugin

```python
from nerimity_sdk import PluginBase, listener

class MyPlugin(PluginBase):
    name = "my_plugin"

    @listener("message:created")
    async def on_message(self, event):
        if "hello" in event.message.content.lower():
            await self.bot.rest.create_message(event.message.channel_id, "Hello!")

async def setup(bot):
    await bot.plugins.load(MyPlugin())
```

See the [Plugins API reference](api/plugins.md) for the full guide.
