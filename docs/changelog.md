---
hide:
  - toc
---

# Changelog

All notable changes to nerimity-sdk. Follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

Nothing yet.

## [1.2.0] — 2026-04-11

### Added in 1.2.0 — Core SDK

- **`I18n`** (`nerimity_sdk.i18n`) — lightweight localization helper. Load JSON locale files, resolve per-guild locale overrides from the bot store, and translate strings with `{placeholder}` substitution via `i18n.t(key, locale, **kwargs)`.
- **`CircuitBreaker`** / **`CircuitOpenError`** (`nerimity_sdk.transport.circuit_breaker`) — async circuit breaker for REST calls. Trips open after *N* consecutive failures and allows a probe call after a configurable recovery timeout. States: `CLOSED → OPEN → HALF_OPEN → CLOSED`.
- **`MiddlewarePipeline`** (`nerimity_sdk.commands.middleware`) — composable middleware chain for prefix commands. Use `pipeline.use(fn)` to stack middleware, `pipeline.build()` to get a single composed middleware, or `@pipeline.apply` to decorate a handler directly. Built-in middleware: `log_middleware`, `guild_only_middleware`, `dm_only_middleware`, `require_permission_middleware(*perms)`.
- **`EventBus`** (`nerimity_sdk.events.bus`) — pub/sub event bus with wildcard topic matching. `*` matches one segment, `**` matches any depth. Supports `subscribe`, `unsubscribe`, `publish`, and `wait_for(pattern, timeout, predicate)` for one-shot async waits.
- **`CooldownManager`** / **`CooldownError`** (`nerimity_sdk.commands.cooldowns`) — sliding-window token-bucket cooldowns. Supports `"user"`, `"server"`, and `"channel"` scopes. Use `cm.check(command, scope_key=..., rate=1, per=5)` or the `@cm.cooldown(rate, per, scope)` decorator.

### Added in 1.2.0 — Contrib plugins

- **`QuizPlugin`** — channel-based trivia quiz game. `/quiz [rounds]` starts a multi-round quiz; first correct answer wins the round. Loads questions from a JSON file or uses the built-in set. `/quizstop` ends the current quiz. Configurable `answer_timeout`.
- **`TagPlugin`** — custom server text snippets. `/tag <name>` retrieves a tag; `/tag add <name> <content>` creates one (mod only); `/tag delete <name>` removes it; `/tag list` shows all tags. Tags are persisted in the bot store. Supports `mod_role_ids` gating.
- **`EconomyPlugin`** — virtual coin economy. `/balance [user]`, `/daily` (24 h cooldown), `/give @user <amount>`, `/richest` (top-10 leaderboard). Configurable `daily_amount`, `currency_name`, `currency_emoji`, and `starting_balance`.
- **`PinboardPlugin`** — community-driven message pinboard. Reacting with the configured emoji (default 📌) nominates a message; once it reaches *threshold* reactions it is forwarded to the pinboard channel (deduped). `/pinboard` shows the last 5 pins.
- **`RaidGuardPlugin`** — automatic lockdown on member-join spike. Monitors join rate; if more than *threshold* members join within *window* seconds an alert is posted to the configured channel. `/raidguard status`, `/raidguard lock`, `/raidguard unlock` (mod only).

## [1.1.0] — 2026-04-11

### Added in 1.1.0
- `RedisRateLimiter` — Redis-backed distributed rate limiter for multi-shard / multi-process bots. All processes sharing a Redis instance coordinate rate limit buckets automatically
- `RateLimitBackend` abstract base class — implement your own rate limit backend by subclassing it
- `LocalRateLimitBackend` — the default in-process backend, same behaviour as before
- `Bot(rate_limiter=...)` — pass any `RateLimitBackend` instance to swap the rate limiter

### Changed in 1.1.0
- `RESTClient` now uses the `RateLimitBackend` interface internally instead of a hardcoded dict of buckets. No behaviour change for existing bots.

## [0.9.0] — 2026-04-10

### Added in 0.9.0
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

### Changed in 0.9.0
- `bot.run()` now auto-restarts on both crash and file save by default
- `Embed` now supports raw dict input in `ctx.reply_embed()`

## [0.8.0] — 2026-03-01

### Added in 0.8.0
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

### Fixed in 0.8.0
- Stale cache entries now marked with `user.stale = True` after reconnect instead of raising

## [0.7.0] — 2026-01-15

### Added in 0.7.0
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

### Changed in 0.7.0
- Type annotation converters — `async def add(ctx, a: int, b: int)` now works without `args=`

## [0.6.0] — 2025-11-20

### Added in 0.6.0
- Plugin system — `PluginBase`, `@listener`, hot-reload via `bot.plugins.load()`
- `nerimity create my-bot` — project scaffolding CLI
- `nerimity version` — show SDK version

## Migration guides

### 0.9 → 1.1

No breaking changes. New features are additive.

### 0.8 → 0.9

No breaking changes. New features are additive.

### 0.7 → 0.8

- `bot.store` is now passed as a constructor argument: `Bot(store=JsonStore("data.json"))` instead of being set after construction.
- Cron tasks now require the `[cron]` extra: `pip install "nerimity-sdk[cron]"`

### 0.6 → 0.7

- `ctx.reply_embed(embed)` replaces the old `ctx.reply(embed=embed)` signature.
- Plugin listeners now use `@listener("event:name")` instead of `@on("event:name")`.
