"""Test utilities: mock gateway and REST so you can unit test without a real connection."""
from __future__ import annotations
import asyncio
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

from nerimity_sdk.bot import Bot
from nerimity_sdk.models import Message, User
from nerimity_sdk.context.ctx import Context


def make_user(id: str = "1", username: str = "TestUser", tag: str = "0001") -> User:
    return User(id=id, username=username, tag=tag, hex_color="#ffffff")


def make_message(
    content: str = "!ping",
    channel_id: str = "100",
    server_id: Optional[str] = None,
    author: Optional[User] = None,
) -> Message:
    return Message(
        id="999",
        channel_id=channel_id,
        type=0,
        content=content,
        created_by=author or make_user(),
        created_at=0,
        server_id=server_id,
    )


def make_context(
    content: str = "!ping",
    channel_id: str = "100",
    server_id: Optional[str] = None,
    bot: Optional[Bot] = None,
) -> Context:
    msg = make_message(content=content, channel_id=channel_id, server_id=server_id)
    rest = MagicMock()
    rest.create_message = AsyncMock(return_value={
        "id": "1000", "channelId": channel_id, "type": 0, "content": "reply",
        "createdBy": {"id": "0", "username": "Bot", "tag": "0000", "hexColor": ""},
        "createdAt": 0,
    })
    cache = bot.cache if bot else __import__("nerimity_sdk.cache.store", fromlist=["Cache"]).Cache()
    emitter = bot.emitter if bot else None
    return Context(msg, rest, cache, [], {}, emitter=emitter)


class MockContext(Context):
    """A Context with a captured reply history for easy assertions.

    Usage::

        ctx = MockContext.create("!ping")
        await ping(ctx)
        ctx.assert_replied_with("Pong! 🏓")
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.replies: list[str] = []
        self.reactions: list[str] = []

    @classmethod
    def create(
        cls,
        content: str = "!ping",
        channel_id: str = "100",
        server_id: Optional[str] = None,
        author_id: str = "1",
    ) -> "MockContext":
        msg = make_message(content=content, channel_id=channel_id,
                           server_id=server_id,
                           author=make_user(id=author_id))
        rest = MagicMock()
        cache = __import__("nerimity_sdk.cache.store", fromlist=["Cache"]).Cache()
        ctx = cls(msg, rest, cache, [], {})

        async def _fake_create_message(channel_id, text, **kw):
            ctx.replies.append(text)
            return {"id": "1000", "channelId": channel_id, "type": 0,
                    "content": text,
                    "createdBy": {"id": "0", "username": "Bot", "tag": "0000", "hexColor": ""},
                    "createdAt": 0}

        async def _fake_add_reaction(channel_id, msg_id, name="", **kw):
            ctx.reactions.append(name)

        rest.create_message = _fake_create_message
        rest.add_reaction = _fake_add_reaction
        return ctx

    def assert_replied_with(self, text: str) -> None:
        assert text in self.replies, (
            f"Expected reply {text!r} not found. Replies were: {self.replies}"
        )

    def assert_replied_contains(self, substring: str) -> None:
        assert any(substring in r for r in self.replies), (
            f"No reply contained {substring!r}. Replies were: {self.replies}"
        )

    def assert_no_reply(self) -> None:
        assert not self.replies, f"Expected no reply but got: {self.replies}"

    def assert_reacted_with(self, emoji: str) -> None:
        assert emoji in self.reactions, (
            f"Expected reaction {emoji!r} not found. Reactions were: {self.reactions}"
        )


class MockBot(Bot):
    """A Bot subclass that never connects to the real gateway — for testing.

    Usage::

        bot = MockBot()

        @bot.command("ping")
        async def ping(ctx):
            await ctx.reply("Pong!")

        async def test_ping():
            await bot.simulate_message("!ping")
            # or use MockContext for direct assertion:
            ctx = MockContext.create("!ping")
            await ping(ctx)
            ctx.assert_replied_with("Pong!")
    """

    def __init__(self, prefix: str = "!", **kwargs) -> None:
        super().__init__(token="mock_token", prefix=prefix, **kwargs)
        self.rest.create_message = AsyncMock(return_value={
            "id": "1", "channelId": "100", "type": 0, "content": "",
            "createdBy": {"id": "0", "username": "Bot", "tag": "0000", "hexColor": ""},
            "createdAt": 0,
        })
        self.rest.add_reaction = AsyncMock(return_value={})
        self.rest.remove_reaction = AsyncMock(return_value={})

    async def start(self) -> None:
        self._ready.set()

    async def simulate_message(self, content: str, channel_id: str = "100",
                                server_id: Optional[str] = None,
                                author_id: str = "42") -> None:
        from nerimity_sdk.events.payloads import MessageCreatedEvent
        msg = Message(
            id="999", channel_id=channel_id, type=0, content=content,
            created_by=User(id=author_id, username="Tester", tag="0001", hex_color=""),
            created_at=0, server_id=server_id,
        )
        event = MessageCreatedEvent(message=msg, socket_id="", server_id=server_id)
        await self.emitter.emit("message:created", event)

    async def simulate_event(self, event: str, data: Any = None) -> None:
        from nerimity_sdk.events.payloads import deserialize
        typed = deserialize(event, data) if isinstance(data, dict) else data
        await self.emitter.emit(event, typed)

    async def simulate_slash(self, command: str, args: list | None = None,
                              channel_id: str = "100",
                              server_id: str | None = None,
                              author_id: str = "42") -> None:
        args_str = " ".join(str(a) for a in (args or []))
        content = f"/{command}" + (f" {args_str}" if args_str else "")
        await self.simulate_message(content, channel_id=channel_id,
                                    server_id=server_id, author_id=author_id)
