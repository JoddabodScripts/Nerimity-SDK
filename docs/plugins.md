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
