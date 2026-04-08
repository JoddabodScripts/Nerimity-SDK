"""Slash command router: @bot.slash decorator + dispatch from gateway events."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from nerimity_sdk.transport.rest import RESTClient
    from nerimity_sdk.cache.store import Cache

Handler = Callable[["SlashContext"], Coroutine[Any, Any, None]]


@dataclass
class SlashContext:
    """Context passed to slash command handlers."""
    command_name: str
    args: str          # raw args string from the slash invocation
    channel_id: str
    server_id: Optional[str]
    user_id: str
    rest: "RESTClient"
    cache: "Cache"

    @property
    def user(self):
        return self.cache.users.get(self.user_id)

    @property
    def server(self):
        if self.server_id:
            return self.cache.servers.get(self.server_id)
        return None

    async def reply(self, content: str):
        from nerimity_sdk.models import Message
        data = await self.rest.create_message(self.channel_id, content)
        return Message.from_dict(data)


@dataclass
class SlashCommandDef:
    name: str
    handler: Handler
    description: str = ""
    args_hint: str = ""  # shown in Nerimity's slash UI


class SlashRouter:
    def __init__(self) -> None:
        self._commands: dict[str, SlashCommandDef] = {}

    def slash(self, name: str, *, description: str = "", args_hint: str = ""):
        """Decorator: @bot.slash("ban", description="Ban a user", args_hint="<user_id>")"""
        def decorator(fn: Handler) -> Handler:
            self._commands[name] = SlashCommandDef(
                name=name, handler=fn,
                description=description, args_hint=args_hint,
            )
            return fn
        return decorator

    def to_bot_commands(self) -> list[dict]:
        """Serialize registered slash commands for POST /api/applications/bot/commands."""
        return [
            {"name": cmd.name, "description": cmd.description, "args": cmd.args_hint}
            for cmd in self._commands.values()
        ]

    async def dispatch(self, event: Any, rest: "RESTClient", cache: "Cache") -> bool:
        """Dispatch a message:created event that looks like a slash invocation.

        Nerimity slash commands arrive as regular messages whose content starts
        with the command name (the client prefixes them). We detect them by
        checking if the message content matches a registered slash command name.
        """
        from nerimity_sdk.events.payloads import MessageCreatedEvent
        if isinstance(event, MessageCreatedEvent):
            msg = event.message
        else:
            return False

        content = msg.content.strip()
        parts = content.split(None, 1)
        if not parts:
            return False

        cmd_name = parts[0].lstrip("/")
        cmd = self._commands.get(cmd_name)
        if not cmd:
            return False

        sctx = SlashContext(
            command_name=cmd_name,
            args=parts[1] if len(parts) > 1 else "",
            channel_id=msg.channel_id,
            server_id=msg.server_id,
            user_id=msg.created_by.id,
            rest=rest,
            cache=cache,
        )
        await cmd.handler(sctx)
        return True

    async def sync(self, rest: "RESTClient") -> None:
        """Register all slash commands with Nerimity."""
        if self._commands:
            await rest.register_bot_commands(self.to_bot_commands())
