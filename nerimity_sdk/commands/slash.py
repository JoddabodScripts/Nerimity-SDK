"""Slash command router: @bot.slash decorator + dispatch from gateway events."""
from __future__ import annotations
import shlex
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from nerimity_sdk.transport.rest import RESTClient
    from nerimity_sdk.cache.store import Cache

Handler = Callable[["SlashContext"], Coroutine[Any, Any, None]]
Middleware = Callable[["SlashContext", Callable], Coroutine[Any, Any, None]]


@dataclass
class SlashContext:
    """Context passed to slash command handlers."""
    command_name: str
    raw_args: str          # unparsed arg string
    channel_id: str
    server_id: Optional[str]
    user_id: str
    rest: "RESTClient"
    cache: "Cache"
    args: list = field(default_factory=list)   # populated by converters
    flags: dict = field(default_factory=dict)

    @property
    def user(self):
        return self.cache.users.get(self.user_id)

    @property
    def server(self):
        if self.server_id:
            return self.cache.servers.get(self.server_id)
        return None

    async def reply(self, content: str):
        """Send a response. Returns None silently if bot lacks channel permission (403)."""
        from nerimity_sdk.models import Message
        data = await self.rest.create_message(self.channel_id, content)
        if data is None:
            return None
        return Message.from_dict(data)

    async def defer(self) -> None:
        """Acknowledge the slash command immediately (sends a typing indicator).
        Call this before slow async work to avoid timeout."""
        await self.rest.send_typing(self.channel_id)


@dataclass
class SlashCommandDef:
    name: str
    handler: Handler
    description: str = ""
    args_hint: str = ""
    converters: list = field(default_factory=list)
    middleware: list = field(default_factory=list)
    error_handler: Optional[Callable] = None


class SlashRouter:
    def __init__(self) -> None:
        self._commands: dict[str, SlashCommandDef] = {}
        self._synced: bool = False
        self._global_middleware: list[Middleware] = []

    def use(self, middleware: Middleware) -> None:
        """Register a global middleware applied to every slash command."""
        self._global_middleware.append(middleware)

    def slash(self, name: str, *, description: str = "", args_hint: str = "",
              args: list | None = None, middleware: list | None = None,
              error_handler: Optional[Callable] = None):
        def decorator(fn: Handler) -> Handler:
            self._commands[name] = SlashCommandDef(
                name=name, handler=fn,
                description=description, args_hint=args_hint,
                converters=args or [],
                middleware=middleware or [],
                error_handler=error_handler,
            )
            self._synced = False
            return fn
        return decorator

    def to_bot_commands(self) -> list[dict]:
        return [
            {"name": cmd.name, "description": cmd.description, "args": cmd.args_hint}
            for cmd in self._commands.values()
        ]

    async def dispatch(self, event: Any, rest: "RESTClient", cache: "Cache") -> bool:
        from nerimity_sdk.events.payloads import MessageCreatedEvent
        if isinstance(event, MessageCreatedEvent):
            msg = event.message
        else:
            return False

        content = msg.content.strip()
        parts = content.split(None, 1)
        if not parts:
            return False

        # Nerimity sends slash commands as "/name:botUserId [args]"
        # Strip the leading / and the :botUserId suffix
        cmd_token = parts[0].lstrip("/")
        cmd_name = cmd_token.split(":")[0]
        cmd = self._commands.get(cmd_name)
        if not cmd:
            return False

        raw_args = parts[1] if len(parts) > 1 else ""

        # Parse args the same way prefix commands do
        try:
            tokens = shlex.split(raw_args)
        except ValueError:
            tokens = raw_args.split()

        sctx = SlashContext(
            command_name=cmd_name,
            raw_args=raw_args,
            channel_id=msg.channel_id,
            server_id=msg.server_id,
            user_id=msg.created_by.id,
            rest=rest,
            cache=cache,
            args=tokens,
        )

        # Run converters if defined
        if cmd.converters:
            from nerimity_sdk.commands.converters import convert_args, ConversionError
            try:
                sctx.args = await convert_args(sctx, cmd.converters)  # type: ignore
            except ConversionError as e:
                await sctx.reply(str(e))
                return True

        # Build middleware chain
        all_mw = self._global_middleware + cmd.middleware

        async def run_handler(c: "SlashContext") -> None:
            await cmd.handler(c)

        chain = run_handler
        for mw in reversed(all_mw):
            prev = chain
            async def make_next(c: "SlashContext", _mw=mw, _prev=prev) -> None:
                await _mw(c, _prev)
            chain = make_next

        try:
            await chain(sctx)
        except Exception as exc:
            if cmd.error_handler:
                await cmd.error_handler(sctx, exc)
            else:
                raise
        return True

    async def sync(self, rest: "RESTClient") -> None:
        """Register all slash commands with Nerimity API."""
        if not self._commands or self._synced:
            return
        from nerimity_sdk.utils.logging import get_logger
        try:
            await rest.register_bot_commands(self.to_bot_commands())
            self._synced = True
            get_logger().info(f"[Slash] Synced {len(self._commands)} command(s): {list(self._commands)}")
        except Exception as exc:
            get_logger().error(f"[Slash] Sync failed: {exc}")
