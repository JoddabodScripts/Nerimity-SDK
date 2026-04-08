"""Rich Context object passed to every command/event handler."""
from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from nerimity_sdk.models import Message, User, Server, Channel, Member
    from nerimity_sdk.transport.rest import RESTClient
    from nerimity_sdk.cache.store import Cache
    from nerimity_sdk.events.emitter import EventEmitter
    from nerimity_sdk.commands.buttons import ButtonRouter

_YES = {"yes", "y", "yeah", "yep", "confirm", "ok"}
_NO  = {"no", "n", "nope", "cancel", "abort"}


class Context:
    def __init__(self, message: "Message", rest: "RESTClient",
                 cache: "Cache", args: list[str], flags: dict[str, Any],
                 emitter: Optional["EventEmitter"] = None,
                 button_router: Optional["ButtonRouter"] = None) -> None:
        self.message = message
        self.rest = rest
        self.cache = cache
        self.args = args
        self.flags = flags
        self._emitter = emitter
        self._button_router = button_router

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def author(self) -> "User":
        return self.message.created_by

    @property
    def channel_id(self) -> str:
        return self.message.channel_id

    @property
    def server_id(self) -> Optional[str]:
        return self.message.server_id

    @property
    def server(self) -> Optional["Server"]:
        return self.cache.servers.get(self.server_id) if self.server_id else None

    @property
    def channel(self) -> Optional["Channel"]:
        return self.cache.channels.get(self.channel_id)

    @property
    def member(self) -> Optional["Member"]:
        if self.server_id:
            return self.cache.members.get(f"{self.server_id}:{self.author.id}")
        return None

    @property
    def mentions(self) -> list["User"]:
        """Resolve all [@:id] mentions in the message content to cached Users."""
        from nerimity_sdk.utils.mentions import resolve_mentions
        return resolve_mentions(self.message.content, self.cache)

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def reply(self, content: str) -> "Message":
        from nerimity_sdk.models import Message
        data = await self.rest.create_message(self.channel_id, content)
        return Message.from_dict(data)

    async def react(self, emoji: str, emoji_id: Optional[str] = None,
                    gif: bool = False, webp: bool = False) -> None:
        await self.rest.add_reaction(
            self.channel_id, self.message.id,
            name=emoji, emoji_id=emoji_id, gif=gif, webp=webp,
        )

    async def unreact(self, emoji: str, emoji_id: Optional[str] = None) -> None:
        await self.rest.remove_reaction(self.channel_id, self.message.id, emoji, emoji_id)

    async def send_typing(self) -> None:
        await self.rest.send_typing(self.channel_id)

    # ── Conversation helpers ──────────────────────────────────────────────────

    async def ask(self, prompt: str, timeout: float = 30.0,
                  check=None) -> Optional["Message"]:
        """Send prompt and wait for the author's next message in this channel."""
        await self.reply(prompt)
        if self._emitter is None:
            raise RuntimeError("ctx.ask() requires an emitter")

        future: asyncio.Future = asyncio.get_event_loop().create_future()

        async def _listener(event) -> None:
            from nerimity_sdk.events.payloads import MessageCreatedEvent
            msg = event.message if isinstance(event, MessageCreatedEvent) else None
            if not msg or msg.created_by.id != self.author.id or msg.channel_id != self.channel_id:
                return
            if check and not check(msg):
                return
            if not future.done():
                future.set_result(msg)

        self._emitter.once("message:created", _listener)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._emitter.off("message:created", _listener)
            return None

    async def confirm(self, prompt: str, timeout: float = 30.0) -> Optional[bool]:
        """Ask a yes/no question. Returns True, False, or None on timeout.

        Usage::

            if not await ctx.confirm("Delete 500 messages? (yes/no)"):
                return await ctx.reply("Cancelled.")
        """
        response = await self.ask(
            f"{prompt} (yes/no)",
            timeout=timeout,
            check=lambda m: m.content.strip().lower() in _YES | _NO,
        )
        if response is None:
            return None
        return response.content.strip().lower() in _YES

    # ── Fetch helpers ─────────────────────────────────────────────────────────

    async def fetch_member(self, user_id: str) -> Optional["Member"]:
        if not self.server_id:
            return None
        return self.cache.members.get(f"{self.server_id}:{user_id}")

    async def fetch_messages(self, limit: int = 50, before: Optional[str] = None,
                              after: Optional[str] = None) -> list["Message"]:
        from nerimity_sdk.models import Message
        raw = await self.rest.fetch_messages(self.channel_id, limit, before, after)
        return [Message.from_dict(m) for m in raw]
