"""Central Bot class."""
from __future__ import annotations
import asyncio
import logging
import os
import signal
from typing import Any, Callable, Coroutine, Literal, Optional, TYPE_CHECKING, overload

if TYPE_CHECKING:
    from nerimity_sdk.events.payloads import (
        MessageCreatedEvent, MessageUpdatedEvent, MessageDeletedEvent,
        MemberJoinedEvent, MemberLeftEvent, ReactionAddedEvent,
        ReactionRemovedEvent, PresenceUpdatedEvent, TypingEvent,
    )

from nerimity_sdk.transport.gateway import GatewayClient
from nerimity_sdk.transport.rest import RESTClient
from nerimity_sdk.events.emitter import EventEmitter
from nerimity_sdk.commands.router import CommandRouter
from nerimity_sdk.commands.slash import SlashRouter
from nerimity_sdk.commands.buttons import ButtonRouter, ButtonContext
from nerimity_sdk.commands.prefix import PrefixResolver, PrefixStore
from nerimity_sdk.cache.store import Cache
from nerimity_sdk.plugins.manager import PluginManager
from nerimity_sdk.scheduler import Scheduler
from nerimity_sdk.storage import MemoryStore, Store
from nerimity_sdk.utils.logging import configure_logger, get_logger
from nerimity_sdk.models import Message, User

__version__ = "1.3.1"


class Bot:
    """
    The main Nerimity bot client.

    Usage::

        bot = Bot(token="YOUR_TOKEN", prefix="/")

        @bot.command("ping")
        async def ping(ctx):
            await ctx.reply("Pong!")

        @bot.slash("ban", description="Ban a user")
        async def ban(sctx):
            await sctx.reply(f"Banned {sctx.args}")

        @bot.button("confirm:{action}:{target}")
        async def on_confirm(bctx):
            await bctx.reply(f"Confirmed: {bctx.params['action']}")

        @bot.on_command_error
        async def on_error(ctx, error):
            await ctx.reply(f"Error: {error}")

        bot.run()
    """

    def __init__(
        self,
        token: str,
        prefix: str = "/",
        prefix_store: Optional[PrefixStore] = None,
        cache_size: int = 1000,
        cache_ttl: float = 0,
        cache_invalidate_on_disconnect: bool = True,
        debug: bool = False,
        watch: bool = False,
        watch_paths: Optional[list[str]] = None,
        store: Optional[Store] = None,
        shard_id: int = 0,
        shard_count: int = 1,
        logger=None,
        json_logs: bool = False,
        health_port: Optional[int] = None,
        disable_builtin_stats: bool = True,
        stats_code: Optional[str] = None,
        rate_limiter: Optional["RateLimitBackend"] = None,
    ) -> None:
        configure_logger(
            level=logging.DEBUG if debug else logging.INFO,
            debug_payloads=debug,
            json_logs=json_logs,
        )
        self.logger = logger or get_logger()
        self.token = token
        self.debug = debug
        self.shard_id = shard_id
        self.shard_count = shard_count
        self._invalidate_on_disconnect = cache_invalidate_on_disconnect
        self._start_time: float = 0.0
        self._messages_seen: int = 0
        self._commands_dispatched: int = 0
        self._watch = watch
        self._watch_paths = watch_paths

        self.emitter = EventEmitter()
        self.rest = RESTClient(token, rate_limiter=rate_limiter)
        # Wire ratelimit callback (set after _ratelimit_handler is defined)
        _bot_ref = self
        async def _rl_cb(route: str, retry_after: float) -> None:
            if _bot_ref._ratelimit_handler:
                await _bot_ref._ratelimit_handler(route, retry_after)
        self.rest._ratelimit_callback = _rl_cb
        self.cache = Cache(max_size=cache_size, ttl=cache_ttl)
        self.prefix_resolver = PrefixResolver(default=prefix, store=prefix_store)
        self.router = CommandRouter(prefix=prefix)
        self.slash_router = SlashRouter()
        self.button_router = ButtonRouter()
        self.plugins = PluginManager(self)
        self.scheduler = Scheduler()
        self.store: Store = store or MemoryStore()

        self._gateway: Optional[GatewayClient] = None
        self._me: Optional[User] = None
        self._ready = asyncio.Event()
        self._watcher = None

        # Error handler hooks (set via decorators)
        self._command_error_handler: Optional[Callable] = None
        self._slash_error_handler: Optional[Callable] = None
        self._button_error_handler: Optional[Callable] = None
        self._ratelimit_handler: Optional[Callable] = None
        self._middleware: list[Callable] = []

        # Wire internal gateway events
        self.emitter.on("user:authenticated", self._on_authenticated)
        self.emitter.on("message:created", self._on_message_created)
        self.emitter.on("message:button_clicked", self._on_button_clicked)
        self.emitter.on("server:member_joined", self._on_member_joined)
        self.emitter.on("server:member_left", self._on_member_left)
        self.emitter.on("server:updated", self._on_server_updated)
        self.emitter.on("server:channel_created", self._on_channel_upsert)
        self.emitter.on("server:channel_updated", self._on_channel_upsert)
        self.emitter.on("server:channel_deleted", self._on_channel_deleted)
        self.emitter.on("disconnect", self._on_disconnect)
        self.emitter.on("inbox:opened", self._on_inbox_opened)

        # Built-in /stats command
        if not disable_builtin_stats:
            _stats_code = stats_code  # capture for closure

            @self.router.command("stats", description="Show bot runtime stats", public=False)
            async def _builtin_stats(ctx):
                # If a code is required, silently ignore wrong/missing codes
                if _stats_code:
                    if not ctx.rest_text or ctx.rest_text.strip() != _stats_code:
                        return
                s = self.stats
                up = s["uptime_seconds"]
                h, rem = divmod(int(up), 3600)
                m, sec = divmod(rem, 60)
                await ctx.reply(
                    f"📊 **Bot Stats**\n"
                    f"⏱ Uptime: `{h:02d}:{m:02d}:{sec:02d}`\n"
                    f"💬 Messages seen: `{s['messages_seen']}`\n"
                    f"⚡ Commands dispatched: `{s['commands_dispatched']}`\n"
                    f"🚦 Rate limit hits: `{s['rate_limit_hits']}`\n"
                    f"🗄 Cache — users: `{s['cached_users']}` "
                    f"servers: `{s['cached_servers']}` "
                    f"channels: `{s['cached_channels']}` "
                    f"members: `{s['cached_members']}`"
                )

    # ── Decorators ────────────────────────────────────────────────────────────

    def on(self, event: str):
        """Listen for an event every time it happens.

        Usage::

            @bot.on("message:created")
            async def handler(event): ...

        Use "*" to listen to every event::

            @bot.on("*")
            async def log_all(event): ...
        """
        def decorator(fn):
            self.emitter.on(event, fn)
            return fn
        return decorator

    def once(self, event: str):
        """Listen for an event only the first time it happens, then stop.

        Usage::

            @bot.once("ready")
            async def on_first_ready(me): ...
        """
        def decorator(fn):
            self.emitter.once(event, fn)
            return fn
        return decorator

    def command(self, name: str, **kwargs):
        """Register a command that works as both !name and /name.

        Shows up in Nerimity's slash menu AND responds to the prefix version.

        Usage::

            @bot.command("ping", description="Check if the bot is alive")
            async def ping(ctx):
                await ctx.reply("Pong!")

            # Require a permission:
            @bot.command("ban", requires=Permissions.BAN_MEMBERS)
            async def ban(ctx): ...
        """
        return self.router.command(name, public=True, **kwargs)

    def command_private(self, name: str, **kwargs):
        """Register a prefix-only command — it will NOT appear in the / menu.

        Use this for admin/debug commands you don't want users to discover.

        Usage::

            @bot.command_private("debug")
            async def debug(ctx):
                await ctx.reply("secret info")
        """
        return self.router.command(name, public=False, **kwargs)

    def slash(self, name: str, **kwargs):
        """Same as @bot.command — alias for people who prefer the name 'slash'."""
        return self.command(name, **kwargs)

    def slash_private(self, name: str, **kwargs):
        """Same as @bot.command_private — alias for people who prefer the name 'slash'."""
        return self.command_private(name, **kwargs)

    def button(self, pattern: str, ttl: Optional[float] = None):
        """Handle a button click. The pattern matches the button's ID.

        Use {name} segments to capture dynamic parts of the ID.
        Note: colons are not allowed in button IDs — use underscores instead.

        Usage::

            @bot.button("confirm_{action}")
            async def on_confirm(bctx):
                await bctx.popup("Done!", f"You confirmed: {bctx.params['action']}")

        ttl: how many seconds before this handler expires (None = never)
        """
        return self.button_router.button(pattern, ttl=ttl)

    def cron(self, expr: str):
        """Run a function on a schedule using a cron expression.

        A cron expression is 5 fields: minute hour day month weekday
        Examples:
            "0 9 * * *"    — every day at 09:00 UTC
            "0 9 * * 1"    — every Monday at 09:00 UTC
            "*/30 * * * *" — every 30 minutes

        Requires: pip install "nerimity-sdk[cron]"

        Usage::

            @bot.cron("0 9 * * 1")
            async def weekly():
                await bot.rest.create_message("CHANNEL_ID", "Good morning!")
        """
        return self.scheduler.cron(expr)

    def disable_command(self, name: str, server_id: str | None = None) -> None:
        """Disable a command globally or for a specific server.

        Usage::

            bot.disable_command("ping")              # globally
            bot.disable_command("ping", server_id)   # per-server
        """
        self.router.disable(name, server_id)

    def enable_command(self, name: str, server_id: str | None = None) -> None:
        """Re-enable a previously disabled command."""
        self.router.enable(name, server_id)

    @overload
    async def wait_for(self, event: Literal["message:created"], *, check=None, timeout: float=60.0) -> "MessageCreatedEvent": ...
    @overload
    async def wait_for(self, event: Literal["message:updated"], *, check=None, timeout: float=60.0) -> "MessageUpdatedEvent": ...
    @overload
    async def wait_for(self, event: Literal["message:deleted"], *, check=None, timeout: float=60.0) -> "MessageDeletedEvent": ...
    @overload
    async def wait_for(self, event: Literal["server:member_joined"], *, check=None, timeout: float=60.0) -> "MemberJoinedEvent": ...
    @overload
    async def wait_for(self, event: Literal["server:member_left"], *, check=None, timeout: float=60.0) -> "MemberLeftEvent": ...
    @overload
    async def wait_for(self, event: Literal["message:reaction_added"], *, check=None, timeout: float=60.0) -> "ReactionAddedEvent": ...
    @overload
    async def wait_for(self, event: Literal["message:reaction_removed"], *, check=None, timeout: float=60.0) -> "ReactionRemovedEvent": ...
    @overload
    async def wait_for(self, event: Literal["user:presence_update"], *, check=None, timeout: float=60.0) -> "PresenceUpdatedEvent": ...
    @overload
    async def wait_for(self, event: Literal["channel:typing"], *, check=None, timeout: float=60.0) -> "TypingEvent": ...
    @overload
    async def wait_for(self, event: str, *, check=None, timeout: float=60.0) -> Any: ...

    async def wait_for(self, event: str, check=None, timeout: float = 60.0, count: int = 1):
        """Wait for a gateway event matching an optional check function.

        Returns the typed event payload (or a list if count > 1).
        Raises asyncio.TimeoutError if the timeout expires.

        Usage::

            event = await bot.wait_for(
                "server:member_joined",
                check=lambda e: e.server_id == "123",
                timeout=30,
            )

            # Collect 3 reactions:
            reactions = await bot.wait_for(
                "message:reaction_added",
                check=lambda e: e.message_id == msg.id,
                count=3, timeout=60,
            )
        """
        if count == 1:
            future: asyncio.Future = asyncio.get_running_loop().create_future()

            async def _listener(payload) -> None:
                if check and not check(payload):
                    return
                if not future.done():
                    future.set_result(payload)

            self.emitter.once(event, _listener)
            try:
                return await asyncio.wait_for(future, timeout=timeout)
            except asyncio.TimeoutError:
                self.emitter.off(event, _listener)
                raise
        else:
            collected: list = []
            future_n: asyncio.Future = asyncio.get_running_loop().create_future()

            async def _listener_n(payload) -> None:
                if check and not check(payload):
                    return
                collected.append(payload)
                if len(collected) >= count and not future_n.done():
                    future_n.set_result(collected)

            self.emitter.on(event, _listener_n)
            try:
                return await asyncio.wait_for(future_n, timeout=timeout)
            except asyncio.TimeoutError:
                return collected if collected else []
            finally:
                self.emitter.off(event, _listener_n)

    async def collect(self, event: str, *, count: int = 10,
                      timeout: float = 60.0, check=None) -> list:
        """Collect multiple events into a list, stopping at *count* or *timeout*.

        Unlike ``wait_for``, this always returns a list and never raises on timeout.

        Usage::

            messages = await bot.collect(
                "message:created",
                count=5, timeout=30,
                check=lambda e: e.message.channel_id == "123",
            )
        """
        return await self.wait_for(event, check=check, timeout=timeout, count=count)

    @property
    def stats(self) -> dict:
        """Runtime statistics snapshot.

        Returns a dict with:
            uptime_seconds, messages_seen, commands_dispatched,
            cached_users, cached_servers, cached_channels, cached_members
        """
        import time as _time
        return {
            "uptime_seconds": round(_time.monotonic() - self._start_time, 1) if self._start_time else 0,
            "messages_seen": self._messages_seen,
            "commands_dispatched": self._commands_dispatched,
            "cached_users": len(self.cache.users._data),
            "cached_servers": len(self.cache.servers._data),
            "cached_channels": len(self.cache.channels._data),
            "cached_members": len(self.cache.members._data),
            "rate_limit_hits": self.rest.rate_limit_hits,
        }

    @property
    def on_command_error(self):
        """Decorator: @bot.on_command_error async def handler(ctx, error): ..."""
        def decorator(fn):
            self._command_error_handler = fn
            return fn
        return decorator

    @property
    def on_slash_error(self):
        """Decorator: @bot.on_slash_error async def handler(sctx, error): ..."""
        def decorator(fn):
            self._slash_error_handler = fn
            return fn
        return decorator

    @property
    def on_button_error(self):
        """Decorator: @bot.on_button_error async def handler(bctx, error): ..."""
        def decorator(fn):
            self._button_error_handler = fn
            return fn
        return decorator

    @property
    def on_ratelimit(self):
        """Decorator: fires when the bot hits a 429 rate limit.

        Usage::

            @bot.on_ratelimit
            async def handler(route: str, retry_after: float): ...
        """
        def decorator(fn):
            self._ratelimit_handler = fn
            return fn
        return decorator

    def use(self, fn: Callable) -> Callable:
        """Register a middleware function that runs before every command.

        The middleware receives ``(ctx, next)`` — call ``await next()`` to
        continue to the command handler, or skip it to block the command.

        Usage::

            @bot.use
            async def log_commands(ctx, next):
                print(f"{ctx.author.username}: {ctx.message.content}")
                await next()

            # Or as a regular function call:
            bot.use(my_middleware)
        """
        self._middleware.append(fn)
        return fn

    # ── Internal event handlers ───────────────────────────────────────────────

    async def _on_authenticated(self, event: Any) -> None:
        from nerimity_sdk.events.payloads import ReadyEvent
        if isinstance(event, ReadyEvent):
            self._me = event.user
            self.cache.upsert_user({"id": event.user.id, "username": event.user.username,
                                     "tag": event.user.tag, "hexColor": event.user.hex_color})
            for srv in event.servers:
                self.cache.servers.set(srv.id, srv)
            for ch in event.channels:
                self.cache.channels.set(ch.id, ch)
            for member in event.members:
                self.cache.members.set(f"{member.server_id}:{member.user.id}", member)
            for role in event.roles:
                srv = self.cache.servers.get(role.server_id)
                if srv:
                    srv.roles[role.id] = role
        elif isinstance(event, dict) and isinstance(event.get("user"), dict):
            self._me = self.cache.upsert_user(event["user"])

        self._ready.set()
        import time as _time
        self._start_time = _time.monotonic()
        self.logger.info(f"[Bot] Ready as {self._me.username if self._me else 'unknown'}")
        # Sync public commands to Nerimity API
        await self._sync_commands()
        self.scheduler.start_all()
        await self.plugins.dispatch_ready()
        await self.emitter.emit("ready", self._me)

    async def _on_message_created(self, event: Any) -> None:
        from nerimity_sdk.events.payloads import MessageCreatedEvent
        from nerimity_sdk.context.ctx import Context

        if isinstance(event, MessageCreatedEvent):
            msg = event.message
        elif isinstance(event, dict):
            msg = Message.from_dict(event.get("message", event))
        else:
            return

        self._messages_seen += 1

        prefix = await self.prefix_resolver.resolve(msg.server_id)
        ctx = Context(msg, self.rest, self.cache, [], {},
                      emitter=self.emitter, button_router=self.button_router)

        # Normalise slash invocations: "/ping:botId args" → "!ping args"
        content = msg.content or ""
        if content.startswith("/"):
            # strip leading / and :botUserId suffix from command token
            parts = content[1:].split(None, 1)
            cmd_token = parts[0].split(":")[0]
            rest_of = parts[1] if len(parts) > 1 else ""
            content = f"{prefix}{cmd_token} {rest_of}".strip()
            # Use a copy so the original Message object is not mutated
            from nerimity_sdk.models import Message as _Msg
            import dataclasses
            msg = dataclasses.replace(msg, content=content)
            ctx = Context(msg, self.rest, self.cache, [], {},
                          emitter=self.emitter, button_router=self.button_router)

        old_prefix = self.router.prefix
        self.router.prefix = prefix
        try:
            handled = await self._dispatch_command(ctx)
        finally:
            self.router.prefix = old_prefix

        if not handled:
            await self.emitter.emit("message", msg)

    async def _sync_commands(self) -> None:
        """Register all public commands with the Nerimity API."""
        seen: set[str] = set()
        public = []
        for cmd in self.router._commands.values():
            if not cmd.public:
                continue
            entry = {"name": cmd.name, "description": cmd.description, "args": cmd.usage}
            if cmd.name not in seen:
                seen.add(cmd.name)
                public.append(entry)
            # Also sync aliases as separate slash commands
            for alias in cmd.aliases:
                if alias not in seen:
                    seen.add(alias)
                    public.append({"name": alias, "description": cmd.description, "args": cmd.usage})
        if not public:
            return
        try:
            await self.rest.register_bot_commands(public)
            self.logger.info(f"[Bot] Synced {len(public)} command(s): {[c['name'] for c in public]}")
        except Exception as exc:
            self.logger.error(f"[Bot] Command sync failed: {exc}")

    async def _dispatch_command(self, ctx) -> bool:
        try:
            # Build middleware chain around the actual dispatch
            async def _run_command():
                handled = await self.router.dispatch(ctx)
                if handled:
                    self._commands_dispatched += 1
                return handled

            if self._middleware:
                result = [False]
                async def _make_next(i):
                    async def _next():
                        if i < len(self._middleware):
                            await self._middleware[i](ctx, await _make_next(i + 1))
                        else:
                            result[0] = await _run_command()
                    return _next
                await (await _make_next(0))()
                return result[0]
            else:
                return await _run_command()
        except Exception as exc:
            if self._command_error_handler:
                await self._command_error_handler(ctx, exc)
            else:
                self.logger.error(f"[Command] Unhandled error: {exc}")
            return True

    async def _dispatch_slash(self, event: Any) -> bool:
        from nerimity_sdk.events.payloads import MessageCreatedEvent
        from nerimity_sdk.commands.slash import SlashContext
        try:
            return await self.slash_router.dispatch(event, self.rest, self.cache)
        except Exception as exc:
            if self._slash_error_handler:
                msg = event.message if isinstance(event, MessageCreatedEvent) else None
                if msg:
                    sctx = SlashContext("", "", msg.channel_id, msg.server_id,
                                        msg.created_by.id, self.rest, self.cache)
                    await self._slash_error_handler(sctx, exc)
            else:
                self.logger.error(f"[Slash] Unhandled error: {exc}")
            return True

    async def _on_button_clicked(self, event: Any) -> None:
        data = event if isinstance(event, dict) else {}
        bctx = ButtonContext(data, self.rest, self.cache)
        try:
            await self.button_router.dispatch(bctx)
        except Exception as exc:
            if self._button_error_handler:
                await self._button_error_handler(bctx, exc)
            else:
                self.logger.error(f"[Button] Unhandled error: {exc}")

    async def _on_member_joined(self, event: Any) -> None:
        from nerimity_sdk.events.payloads import MemberJoinedEvent
        if isinstance(event, MemberJoinedEvent):
            self.cache.members.set(f"{event.server_id}:{event.member.user.id}", event.member)
        elif isinstance(event, dict):
            self.cache.upsert_member(event)

    async def _on_member_left(self, event: Any) -> None:
        from nerimity_sdk.events.payloads import MemberLeftEvent
        if isinstance(event, MemberLeftEvent):
            self.cache.members.delete(f"{event.server_id}:{event.user_id}")
        elif isinstance(event, dict):
            self.cache.members.delete(f"{event.get('serverId')}:{event.get('userId')}")

    async def _on_server_updated(self, event: Any) -> None:
        from nerimity_sdk.events.payloads import ServerUpdatedEvent
        if isinstance(event, ServerUpdatedEvent):
            srv = self.cache.servers.get(event.server_id)
            if srv:
                srv.merge(event.updated)

    async def _on_channel_upsert(self, event: Any) -> None:
        from nerimity_sdk.events.payloads import ChannelCreatedEvent, ChannelUpdatedEvent
        if isinstance(event, ChannelCreatedEvent):
            self.cache.channels.set(event.channel.id, event.channel)
        elif isinstance(event, ChannelUpdatedEvent):
            ch = self.cache.channels.get(event.channel_id)
            if ch:
                ch.merge(event.updated)
        elif isinstance(event, dict):
            self.cache.upsert_channel(event)

    async def _on_channel_deleted(self, event: Any) -> None:
        from nerimity_sdk.events.payloads import ChannelDeletedEvent
        if isinstance(event, ChannelDeletedEvent):
            self.cache.channels.delete(event.channel_id)

    async def _on_inbox_opened(self, event: Any) -> None:
        """inbox:opened — a DM channel was opened. Cache the channel."""
        data = event if isinstance(event, dict) else {}
        channel_data = data.get("channel") or data
        if isinstance(channel_data, dict) and "id" in channel_data:
            self.cache.upsert_channel(channel_data)

    async def _on_disconnect(self, _: Any) -> None:
        if self._invalidate_on_disconnect:
            self.logger.warning("[Bot] Disconnected — marking cache stale")
            self.cache.mark_all_stale()
        self._ready.clear()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._watch:
            from nerimity_sdk.devtools.watcher import Watcher
            self._watcher = Watcher(self, self._watch_paths)
            await self._watcher.start()
        self._gateway = GatewayClient(
            self.token, self.emitter,
            shard_id=self.shard_id, shard_count=self.shard_count,
        )
        await self._gateway.connect()
        if self._health_port:
            from nerimity_sdk.health import HealthServer
            self._health_server = HealthServer(self, self._health_port)
            await self._health_server.start()

    async def close(self) -> None:
        self.logger.info("[Bot] Shutting down...")
        self.scheduler.stop_all()
        if self._watcher:
            self._watcher.stop()
        if self._gateway:
            await self._gateway.disconnect()
        if self._health_server:
            await self._health_server.stop()
        await self.rest.close()
        self.logger.info("[Bot] Goodbye.")

    def run(self, auto_restart: bool = True) -> None:
        # If we're the parent process, hand off to the watchdog runner.
        # The runner re-executes this same script as a child with NERIMITY_CHILD=1,
        # restarting it on crash or .py file changes.
        if auto_restart and os.environ.get("NERIMITY_CHILD") != "1":
            import __main__
            script = getattr(__main__, "__file__", None)
            if script:
                from nerimity_sdk._runner import launch
                launch(script)
                return

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _run():
            _closing = False

            async def _shutdown():
                nonlocal _closing
                if _closing:
                    return
                _closing = True
                await self.close()

            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown()))
                except NotImplementedError:
                    pass
            try:
                await self.start()
            except asyncio.CancelledError:
                pass
            finally:
                if not _closing:
                    await self.close()

        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()

    @classmethod
    def from_shard(cls, token: str, shard_id: int, shard_count: int, **kwargs) -> "Bot":
        return cls(token=token, shard_id=shard_id, shard_count=shard_count, **kwargs)
