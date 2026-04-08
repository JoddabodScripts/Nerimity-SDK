"""Test utilities: mock gateway and REST so you can unit test without a real connection."""
from __future__ import annotations
import asyncio
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

from nerimity_sdk.bot import Bot
from nerimity_sdk.models import Message, User, Channel, Server
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


class MockBot(Bot):
    """A Bot subclass that never connects to the real gateway — for testing."""

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
        from nerimity_sdk.models import Message, User
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
