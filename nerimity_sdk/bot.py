"""Central Bot class."""
from __future__ import annotations
import asyncio
import logging
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

__version__ = "0.3.1"


class Bot:
    """
    The main Nerimity bot client.

    Usage::

        bot = Bot(token="YOUR_TOKEN", prefix="!")

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
        prefix: str = "!",
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
    ) -> None:
        configure_logger(
            level=logging.DEBUG if debug else logging.INFO,
            debug_payloads=debug,
        )
        self.logger = logger or get_logger()
        self.token = token
        self.debug = debug
        self.shard_id = shard_id
        self.shard_count = shard_count
        self._invalidate_on_disconnect = cache_invalidate_on_disconnect
        self._watch = watch
        self._watch_paths = watch_paths

        self.emitter = EventEmitter()
        self.rest = RESTClient(token)
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

        # Wire internal gateway events
        self.emitter.on("user:authenticated", self._on_authenticated)
        self.emitter.on("message:created", self._on_message_created)
        self.emitter.on("message:button_clicked_callback", self._on_button_clicked)
        self.emitter.on("server:member_joined", self._on_member_joined)
        self.emitter.on("server:member_left", self._on_member_left)
        self.emitter.on("server:updated", self._on_server_updated)
        self.emitter.on("server:channel_created", self._on_channel_upsert)
        self.emitter.on("server:channel_updated", self._on_channel_upsert)
        self.emitter.on("server:channel_deleted", self._on_channel_deleted)
        self.emitter.on("disconnect", self._on_disconnect)
        self.emitter.on("inbox:opened", self._on_inbox_opened)

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

        Usage::

            @bot.button("confirm:{action}")
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

    async def wait_for(self, event: str, check=None, timeout: float = 60.0):
        """Wait for a gateway event matching an optional check function.

        Returns the typed event payload, or raises asyncio.TimeoutError.

        Usage::

            event = await bot.wait_for(
                "server:member_joined",
                check=lambda e: e.server_id == "123",
                timeout=30,
            )
        """
        future: asyncio.Future = asyncio.get_event_loop().create_future()

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
            msg.content = f"{prefix}{cmd_token} {rest_of}".strip()

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
        public = [
            {"name": cmd.name, "description": cmd.description, "args": cmd.usage}
            for cmd in self.router._commands.values()
            if cmd.public
        ]
        if not public:
            return
        try:
            await self.rest.register_bot_commands(public)
            self.logger.info(f"[Bot] Synced {len(public)} command(s): {[c['name'] for c in public]}")
        except Exception as exc:
            self.logger.error(f"[Bot] Command sync failed: {exc}")

    async def _dispatch_command(self, ctx) -> bool:
        try:
            return await self.router.dispatch(ctx)
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

    async def close(self) -> None:
        self.logger.info("[Bot] Shutting down...")
        self.scheduler.stop_all()
        if self._watcher:
            self._watcher.stop()
        if self._gateway:
            await self._gateway.disconnect()
        await self.rest.close()
        self.logger.info("[Bot] Goodbye.")

    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _run():
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, lambda: asyncio.create_task(self.close()))
                except NotImplementedError:
                    pass
            try:
                await self.start()
            except asyncio.CancelledError:
                pass
            finally:
                await self.close()

        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()

    @classmethod
    def from_shard(cls, token: str, shard_id: int, shard_count: int, **kwargs) -> "Bot":
        return cls(token=token, shard_id=shard_id, shard_count=shard_count, **kwargs)
