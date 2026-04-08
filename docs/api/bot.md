# Bot

The central class. Import and instantiate once per process.

```python
from nerimity_sdk import Bot
bot = Bot(token="YOUR_TOKEN", prefix="!")
```

## Decorators

### `@bot.on(event)`
Register an async listener for a gateway event. Receives a typed payload object.

```python
@bot.on("message:created")
async def handler(event: MessageCreatedEvent): ...

@bot.on("ready")
async def on_ready(me: User): ...

@bot.on("*")          # wildcard — fires for every event
async def log_all(data): ...
```

### `@bot.once(event)`
Same as `on()` but fires only once.

### `@bot.command(name, **kwargs)`
Register a prefix command. See [Commands](commands.md).

### `@bot.slash(name, **kwargs)`
Register a slash command. See [Slash Commands](slash.md).

### `@bot.button(pattern, ttl=None)`
Register a button handler. See [Buttons](buttons.md).

### `@bot.cron(expr)`
Register a scheduled task. See [Scheduler](scheduler.md).

### `@bot.on_command_error`
```python
@bot.on_command_error
async def handler(ctx: Context, error: Exception): ...
```

### `@bot.on_slash_error`
```python
@bot.on_slash_error
async def handler(sctx: SlashContext, error: Exception): ...
```

### `@bot.on_button_error`
```python
@bot.on_button_error
async def handler(bctx: ButtonContext, error: Exception): ...
```

## Properties

| Property | Type | Description |
|---|---|---|
| `bot.rest` | `RESTClient` | Direct HTTP API access |
| `bot.cache` | `Cache` | In-memory object cache |
| `bot.store` | `Store` | Persistent key-value storage |
| `bot.plugins` | `PluginManager` | Load/unload/reload plugins |
| `bot.scheduler` | `Scheduler` | Cron job manager |
| `bot.prefix_resolver` | `PrefixResolver` | Per-guild prefix config |
| `bot.router` | `CommandRouter` | Prefix command router |
| `bot.slash_router` | `SlashRouter` | Slash command router |
| `bot.button_router` | `ButtonRouter` | Button handler router |

## Methods

### `bot.run()`
Blocking entry point. Handles `SIGINT`/`SIGTERM` gracefully.

### `await bot.start()`
Async version — use if you need to run alongside other async code.

### `await bot.close()`
Flush queues, stop scheduler, disconnect gateway, close HTTP session.

### `Bot.from_shard(token, shard_id, shard_count, **kwargs)`
Create a bot instance for a specific shard (architecture is ready; Nerimity sharding is a stub).
