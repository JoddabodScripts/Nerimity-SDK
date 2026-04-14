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
    """Everything you need inside a command handler.

    Passed automatically to every @bot.command handler. You don't create this yourself.

    Quick reference:
        ctx.author          → User who sent the command
        ctx.server          → Server it was sent in (None in DMs)
        ctx.channel_id      → Channel ID to reply to
        ctx.args            → Parsed positional arguments (converted if args= set)
        ctx.flags           → --flag=value flags from the message
        ctx.mentions        → [@:id] mentions resolved to User objects

        await ctx.reply("hi")                   → send a message
        await ctx.react("👍")                   → react to the triggering message
        await ctx.ask("Your name?")             → wait for author's next message
        await ctx.confirm("Sure?")              → yes/no prompt → True/False/None
        await ctx.author.send(bot.rest, "hi")   → send a DM to the author
    """
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
        """Author's server member from cache. Use await ctx.fetch_member(id) for API fallback."""
        if self.server_id:
            return self.cache.members.get(f"{self.server_id}:{self.author.id}")
        return None

    async def ensure_member(self) -> Optional["Member"]:
        """Like ctx.member but falls back to the API if not cached."""
        return await self.fetch_member(self.author.id)

    @property
    def mentions(self) -> list["User"]:
        """Resolve all [@:id] mentions in the message content to cached Users."""
        from nerimity_sdk.utils.mentions import resolve_mentions
        return resolve_mentions(self.message.content, self.cache)

    @property
    def rest_text(self) -> str:
        """All remaining args joined as a single string."""
        return " ".join(self.args)

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def reply(self, content: str, buttons: list | None = None) -> "Message":
        from nerimity_sdk.models import Message
        btn_data = None
        if buttons is not None:
            from nerimity_sdk.commands.buttons import Button
            btn_data = [
                {"label": str(b.label), "id": str(b.id), "alert": getattr(b, "alert", False)}
                for b in buttons
            ]
        data = await self.rest.create_message(self.channel_id, content, buttons=btn_data)
        self._last_reply: Optional["Message"] = Message.from_dict(data)
        return self._last_reply

    async def edit_reply(self, content: str, buttons: list | None = None) -> "Message":
        """Edit the bot's most recent reply in this context.

        Sends a new message if no reply has been sent yet.

        Usage::

            msg = await ctx.reply("Loading...")
            await asyncio.sleep(1)
            await ctx.edit_reply("Done! ✅")
        """
        if not hasattr(self, "_last_reply") or self._last_reply is None:
            return await self.reply(content, buttons=buttons)
        return await self.edit(self._last_reply.id, content, buttons=buttons)

    async def reply_silent(self, content: str) -> "Message":
        """Send a message that doesn't trigger a notification."""
        from nerimity_sdk.models import Message
        from nerimity_sdk.commands.builders import MessageBuilder
        data = await self.rest.request(
            "POST", f"/channels/{self.channel_id}/messages",
            json=MessageBuilder().content(content).silent().build()
        )
        return Message.from_dict(data)

    async def reply_file(self, path: str, content: str = "") -> "Message":
        """Upload a file to the Nerimity CDN then send it in this channel.

        Usage::

            await ctx.reply_file("image.png")
            await ctx.reply_file("report.txt", content="Here's the report:")
        """
        from nerimity_sdk.models import Message
        file_id = await self.rest.upload_file(path)
        data = await self.rest.create_message(self.channel_id, content,
                                               nerimity_file_id=file_id)
        return Message.from_dict(data)

    async def edit(self, message_id: str, content: str,
                   buttons: list | None = None) -> "Message":
        """Edit one of the bot's own messages, optionally updating buttons too."""
        from nerimity_sdk.models import Message
        btn_data = None
        if buttons is not None:
            btn_data = [
                {"label": str(b.label), "id": str(b.id), "alert": getattr(b, "alert", False)}
                for b in buttons
            ]
        data = await self.rest.update_message(self.channel_id, message_id, content,
                                               buttons=btn_data)
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

    def typing(self) -> "_TypingContext":
        """Async context manager that sends a typing indicator while work is done.

        Usage::

            async with ctx.typing():
                result = await slow_operation()
            await ctx.reply(result)
        """
        return _TypingContext(self)

    # ── Conversation helpers ──────────────────────────────────────────────────

    async def ask(self, prompt: str, timeout: float = 30.0,
                  check=None) -> Optional["Message"]:
        """Send prompt and wait for the author's next message in this channel."""
        await self.reply(prompt)
        if self._emitter is None:
            raise RuntimeError("ctx.ask() requires an emitter")

        future: asyncio.Future = asyncio.get_running_loop().create_future()

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
        """Fetch a member by user ID. Falls back to API if not in cache."""
        if not self.server_id:
            return None
        cached = self.cache.members.get(f"{self.server_id}:{user_id}")
        if cached:
            return cached
        try:
            from nerimity_sdk.models import Member
            data = await self.rest.request("GET", f"/servers/{self.server_id}/members/{user_id}")
            if data:
                member = Member.from_dict(data)
                self.cache.members.set(f"{self.server_id}:{user_id}", member)
                return member
        except Exception:
            pass
        return None

    async def reply_embed(self, embed: "Any") -> "Message":
        """Send an embed. Accepts an Embed builder object or a raw HTML string."""
        from nerimity_sdk.models import Message
        if isinstance(embed, str):
            html = embed
        elif isinstance(embed, dict):
            html = embed.get("htmlEmbed", "")
        else:
            html = embed.to_html()
        data = await self.rest.create_message(self.channel_id, "\u200b",
                                               embed={"htmlEmbed": html})
        return Message.from_dict(data)

    async def pin(self) -> None:
        """Pin the triggering message in this channel."""
        await self.rest.pin_message(self.channel_id, self.message.id)

    async def delete(self) -> None:
        """Delete the triggering message."""
        await self.rest.delete_message(self.channel_id, self.message.id)

    async def reply_paginated(self, text: str, max_length: int = 1800) -> None:
        """Split long text into pages and send each as a separate message.

        Usage::

            await ctx.reply_paginated(very_long_string)
        """
        chunks = [text[i:i + max_length] for i in range(0, len(text), max_length)]
        for chunk in chunks:
            await self.reply(chunk)

    async def forward(self, channel_id: str) -> "Message":
        """Re-post the triggering message content to another channel."""
        from nerimity_sdk.models import Message
        data = await self.rest.create_message(channel_id, self.message.content or "\u200b")
        return Message.from_dict(data)

    async def reply_dm(self, content: str) -> "Message":
        """Send a DM to the command author instead of replying in the channel."""
        from nerimity_sdk.models import Message
        channel_data = await self.rest.open_dm(self.author.id)
        data = await self.rest.create_message(channel_data["id"], content)
        return Message.from_dict(data)

    async def reply_then_delete(self, content: str, delay: float = 5.0) -> None:
        """Send a message then delete it after `delay` seconds."""
        import asyncio
        msg = await self.reply(content)
        await asyncio.sleep(delay)
        await self.rest.delete_message(self.channel_id, msg.id)

    async def fetch_messages(self, limit: int = 50, before: Optional[str] = None,
                              after: Optional[str] = None) -> list["Message"]:
        from nerimity_sdk.models import Message
        raw = await self.rest.fetch_messages(self.channel_id, limit, before, after)
        return [Message.from_dict(m) for m in raw]


class _TypingContext:
    def __init__(self, ctx: "Context") -> None:
        self._ctx = ctx
        self._task: "asyncio.Task | None" = None

    async def __aenter__(self) -> "_TypingContext":
        async def _keep_typing():
            while True:
                await self._ctx.rest.send_typing(self._ctx.channel_id)
                await asyncio.sleep(4)
        self._task = asyncio.create_task(_keep_typing())
        return self

    async def __aexit__(self, *_) -> None:
        if self._task:
            self._task.cancel()
