# Changelog

All notable changes to nerimity-sdk. Follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

---

## [0.9.0] — 2026-04-10

### Added
- `OAuth2Client` — full authorization code flow with token refresh
- `Webhook` — send messages, embeds, and files to channels without a bot
- `ctx.reply_silent()` — send a message that doesn't trigger notifications
- `ctx.forward(channel_id)` — forward a message to another channel
- `bot.rest.fetch_channel(channel_id)` — fetch a channel object from the API
- `bot.rest.fetch_message(channel_id, message_id)` — fetch a single message
- `Bot(disable_builtin_stats=True)` — opt out of the automatic `/stats` command
- Partial `wait_for` results — `wait_for(count=3)` now returns collected events on timeout instead of raising
- Rate limit hook — `@bot.on_ratelimit async def handler(route, retry_after)`
- Alias slash sync — command aliases are now registered in the slash menu automatically

### Changed
- `bot.run()` now auto-restarts on both crash and file save by default
- `Embed` now supports raw dict input in `ctx.reply_embed()`

---

## [0.8.0] — 2026-03-01

### Added
- `nerimity dev bot.py` — live dev dashboard with pretty logs
- `Bot(health_port=8080)` — health check endpoint (`GET /health`, `GET /stats`)
- `Bot(json_logs=True)` — structured JSON logging
- `bot.stats` — runtime stats (uptime, message count, command count, cache sizes)
- `@bot.cron(...)` — scheduled tasks (requires `pip install "nerimity-sdk[cron]"`)
- `JsonStore`, `SqliteStore`, `RedisStore` — persistent storage backends
- `Paginator` — multi-page replies with navigation buttons
- `ctx.reply_paginated(long_text)` — auto-split long text into pages
- Command groups — `bot.group("mod")` → `/mod ban`, `/mod kick`
- `bot.disable_command()` / `bot.enable_command()` — toggle commands at runtime
- Per-guild prefix — `bot.prefix_resolver.set(server_id, "?")`
- Cooldown scopes — `cooldown_scope="server"` or `"user"` (default)

### Fixed
- Stale cache entries now marked with `user.stale = True` after reconnect instead of raising

---

## [0.7.0] — 2026-01-15

### Added
- Buttons — `Button`, `@bot.button("id_{param}")`
- `ctx.confirm()` — yes/no confirmation prompt
- `ctx.ask()` — wait for a follow-up message
- `bot.wait_for(event, count, timeout)` — collect events programmatically
- `ctx.reply_dm()` — send a DM to the command author
- `ctx.reply_then_delete(delay)` — auto-delete a reply after N seconds
- `ctx.pin()` / `ctx.delete()` — pin or delete the triggering message
- File uploads — `ctx.reply_file("path")`
- Embed builder — `Embed().title().description().field().color()`
- `nerimity lint` — static analysis for common mistakes

### Changed
- Type annotation converters — `async def add(ctx, a: int, b: int)` now works without `args=`

---

## [0.6.0] — 2025-11-20

### Added
- Plugin system — `PluginBase`, `@listener`, hot-reload via `bot.plugins.load()`
- `nerimity create my-bot` — project scaffolding CLI
- `nerimity version` — show SDK version

---

## Migration guides

### 0.8 → 0.9

No breaking changes. New features are additive.

### 0.7 → 0.8

- `bot.store` is now passed as a constructor argument: `Bot(store=JsonStore("data.json"))` instead of being set after construction.
- Cron tasks now require the `[cron]` extra: `pip install "nerimity-sdk[cron]"`

### 0.6 → 0.7

- `ctx.reply_embed(embed)` replaces the old `ctx.reply(embed=embed)` signature.
- Plugin listeners now use `@listener("event:name")` instead of `@on("event:name")`.
