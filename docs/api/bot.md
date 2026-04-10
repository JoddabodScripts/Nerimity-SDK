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
| `bot.stats` | `dict` | Runtime stats: uptime, messages seen, commands dispatched, rate limit hits, cache sizes |

## Health endpoint

```python
bot = Bot(token="...", health_port=8080)
```

Starts a lightweight HTTP server alongside the bot:
- `GET /health` → `{"status": "ok", "uptime": 123.4}`
- `GET /stats` → full `bot.stats` dict as JSON

Useful for uptime monitors, container health checks, and Kubernetes liveness probes.

## Built-in /stats command

Every bot automatically gets a `/stats` slash command that posts a formatted stats embed. No setup needed.

## Methods

### `bot.run(auto_restart=True)`
Blocking entry point. By default, wraps the bot in a watchdog that:
- Restarts automatically on crash
- Restarts when any `.py` file in the project is saved

Pass `auto_restart=False` to disable this behaviour.

### `await bot.wait_for(event, check=None, timeout=60.0, count=1)`
Wait for a gateway event matching an optional check function.

- Returns the typed event payload when `count=1` (default)
- Returns a `list` of payloads when `count > 1`
- Raises `asyncio.TimeoutError` if the timeout expires

```python
# Wait for one event
event = await bot.wait_for(
    "server:member_joined",
    check=lambda e: e.server_id == "123",
    timeout=30,
)

# Collect 3 reactions
reactions = await bot.wait_for(
    "message:reaction_added",
    check=lambda e: e.message_id == msg.id,
    count=3, timeout=60,
)
```

### `await bot.start()`
Async version — use if you need to run alongside other async code.

### `await bot.close()`
Flush queues, stop scheduler, disconnect gateway, close HTTP session.

### `Bot.from_shard(token, shard_id, shard_count, **kwargs)`
Create a bot instance for a specific shard.
