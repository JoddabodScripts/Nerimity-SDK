"""In-memory LRU/TTL cache for servers, channels, members, and users."""
from __future__ import annotations
import time
from collections import OrderedDict
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


class LRUCache(Generic[T]):
    def __init__(self, max_size: int = 1000, ttl: float = 0) -> None:
        self._max = max_size
        self._ttl = ttl
        self._data: OrderedDict[str, tuple[T, float]] = OrderedDict()

    def get(self, key: str) -> Optional[T]:
        if key not in self._data:
            return None
        item, ts = self._data[key]
        if self._ttl and time.monotonic() - ts > self._ttl:
            del self._data[key]
            return None
        self._data.move_to_end(key)
        return item

    def set(self, key: str, value: T) -> None:
        self._data[key] = (value, time.monotonic())
        self._data.move_to_end(key)
        if len(self._data) > self._max:
            self._data.popitem(last=False)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def values(self):
        return [v for v, _ in self._data.values()]


class Cache:
    """Central cache for all Nerimity objects with partial-merge support."""

    def __init__(self, max_size: int = 1000, ttl: float = 0) -> None:
        from nerimity_sdk.models import Server, Channel, User, Member, Message
        self.servers: LRUCache[Server] = LRUCache(max_size, ttl)
        self.channels: LRUCache[Channel] = LRUCache(max_size, ttl)
        self.users: LRUCache[User] = LRUCache(max_size, ttl)
        self.members: LRUCache[Member] = LRUCache(max_size, ttl)
        self.messages: LRUCache[Message] = LRUCache(max_size * 10, ttl)

    # --- Upsert helpers (merge partial data rather than overwrite) ---

    def upsert_user(self, data: dict) -> "User":
        from nerimity_sdk.models import User
        existing = self.users.get(data["id"])
        if existing:
            existing.merge(data)
            return existing
        user = User.from_dict(data)
        self.users.set(user.id, user)
        return user

    def upsert_server(self, data: dict) -> "Server":
        from nerimity_sdk.models import Server
        existing = self.servers.get(data["id"])
        if existing:
            existing.merge(data)
            return existing
        server = Server.from_dict(data)
        self.servers.set(server.id, server)
        return server

    def upsert_channel(self, data: dict) -> "Channel":
        from nerimity_sdk.models import Channel
        existing = self.channels.get(data["id"])
        if existing:
            existing.merge(data)
            return existing
        channel = Channel.from_dict(data)
        self.channels.set(channel.id, channel)
        return channel

    def upsert_member(self, data: dict) -> "Member":
        from nerimity_sdk.models import Member
        user = self.upsert_user(data["user"]) if isinstance(data.get("user"), dict) else None
        server_id = data.get("serverId", "")
        key = f"{server_id}:{user.id if user else data.get('userId', '')}"
        existing = self.members.get(key)
        if existing:
            if "roleIds" in data:
                existing.role_ids = data["roleIds"]
            return existing
        member = Member.from_dict(data)
        self.members.set(key, member)
        return member

    def upsert_message(self, data: dict) -> "Message":
        from nerimity_sdk.models import Message
        if isinstance(data.get("createdBy"), dict):
            self.upsert_user(data["createdBy"])
        msg = Message.from_dict(data)
        self.messages.set(msg.id, msg)
        return msg
