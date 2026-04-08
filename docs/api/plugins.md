# Plugins

Plugins let you split your bot into reloadable modules.

## Creating a plugin

```python
from nerimity_sdk import PluginBase, listener

class ModerationPlugin(PluginBase):
    name = "moderation"
    description = "Moderation commands"

    @listener("server:member_joined")
    async def on_join(self, event):
        # self.bot is the Bot instance
        await self.bot.rest.create_message(
            event.member.server_id, f"Welcome!"
        )

    async def on_load(self):
        print(f"[{self.name}] Loaded")

    async def on_unload(self):
        print(f"[{self.name}] Unloaded")

    async def on_ready(self):
        print(f"[{self.name}] Bot is ready")


async def setup(bot):
    await bot.plugins.load(ModerationPlugin())
```

## Loading

```python
# From an instance
await bot.plugins.load(ModerationPlugin())

# From a file path
await bot.plugins.load_from_path("plugins/moderation.py")
```

## Hot reload

```python
await bot.plugins.reload("moderation")
```

Calls `importlib.reload` on the module, re-instantiates the plugin class, and re-registers all commands and listeners.

## Unloading

```python
await bot.plugins.unload("moderation")
```

## Listing loaded plugins

```python
print(bot.plugins.loaded)   # ["moderation", "welcome", ...]
```

## Watch mode

With `watch=True`, plugins reload automatically when their `.py` file changes:

```python
bot = Bot(token="...", watch=True, watch_paths=["plugins"])
```
