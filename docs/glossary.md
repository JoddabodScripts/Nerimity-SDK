# Glossary

Terms used throughout the docs.

---

**Bot token**
A secret string that authenticates your bot with Nerimity. Treat it like a password. Generated from the developer portal.

**Cache**
An in-memory store of objects the bot has seen (servers, channels, members, users). Populated automatically from gateway events. Faster than an API call but may be stale after a reconnect — check `user.stale`.

**Channel ID / Server ID / User ID**
Unique identifiers for Nerimity objects. Also called **snowflakes** — large integers that encode a timestamp. In the SDK these are always strings.

**Command**
A function triggered by a user message. Prefix commands start with a symbol (e.g. `!ping`). Slash commands start with `/` and appear in Nerimity's command menu.

**Context (`ctx`)**
The object passed to every command handler. Contains the message, author, channel, parsed arguments, and helper methods like `ctx.reply()`.

**Decorator**
A Python syntax (`@something`) that wraps a function. Used throughout the SDK to register handlers: `@bot.command(...)`, `@bot.on(...)`, etc.

**Event**
A notification from the Nerimity gateway that something happened — a message was sent, a member joined, a reaction was added, etc. Listen with `@bot.on("event:name")`.

**Gateway**
The WebSocket connection between your bot and Nerimity. The SDK manages this automatically — it connects, authenticates, receives events, and reconnects on disconnect.

**Guild**
Another word for **server**. Used interchangeably in the SDK (e.g. `guild_only=True`).

**Plugin**
A self-contained module that groups related listeners and commands. Loaded with `await bot.plugins.load(MyPlugin())`. Can be hot-reloaded without restarting the bot.

**Prefix**
The character(s) that trigger prefix commands. Default is `!`. Can be set per-server with `bot.prefix_resolver`.

**REST**
The HTTP API used to perform actions (send messages, kick members, etc.). Accessed via `bot.rest`. Separate from the gateway.

**Shard**
A single gateway connection handling a subset of servers. Only needed for large bots. See [Sharding](sharding.md).

**Slash command**
A command registered with Nerimity's slash command system. Appears in the `/` menu with autocomplete. Registered automatically when you use `@bot.command(description="...")`.

**Snowflake**
Nerimity's ID format — a large integer that encodes a creation timestamp. Always treated as a string in the SDK.

**Store**
Persistent key-value storage that survives bot restarts. Available backends: `JsonStore`, `SqliteStore`, `RedisStore`.

**Token**
See **Bot token**.

**`await`**
Python keyword required before any async operation (sending a message, making an API call, etc.). Needed because these operations take time — `await` lets other code run while waiting.
