# nerimity-sdk-contrib

Ready-made plugins for [nerimity-sdk](https://pypi.org/project/nerimity-sdk/) bots.

```bash
pip install nerimity-sdk-contrib
```

## Plugins

| Plugin | Description |
|---|---|
| `WelcomePlugin` | Greets new members with a configurable message |
| `AutoModPlugin` | Deletes messages matching a word/regex list |
| `StarboardPlugin` | Reposts highly-reacted messages to a starboard channel |
| `LoggingPlugin` | Logs joins, leaves, deletes, and edits to a channel |

## Usage

```python
from nerimity_sdk import Bot
from nerimity_sdk_contrib import WelcomePlugin, AutoModPlugin, StarboardPlugin, LoggingPlugin, RoleMenuPlugin, PollPlugin

bot = Bot(token="...", prefix="!")

@bot.on("ready")
async def on_ready(me):
    await bot.plugins.load(WelcomePlugin(channel_id="123"))
    await bot.plugins.load(AutoModPlugin(blocked=["badword"], log_channel_id="456"))
    await bot.plugins.load(StarboardPlugin(channel_id="789", threshold=3))
    await bot.plugins.load(LoggingPlugin(channel_id="000"))

bot.run()
```

## Adding a new plugin

1. Create `nerimity_sdk_contrib/your_plugin.py` with a class inheriting `PluginBase`
2. Import and re-export it in `__init__.py`
3. Add it to the table above and to the [plugin marketplace docs](https://joddabodscripts.github.io/Nerimity-SDK/plugins/)
