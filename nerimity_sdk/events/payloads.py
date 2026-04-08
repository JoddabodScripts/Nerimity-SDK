"""Typed dataclasses for every Nerimity gateway event payload.

Every event emitted by the SDK carries one of these objects instead of a raw dict.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
from nerimity_sdk.models import (
    User, Message, Server, Channel, Member, Role, Permissions,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user(d: Any) -> Optional[User]:
    return User.from_dict(d) if isinstance(d, dict) else None


def _msg(d: Any) -> Optional[Message]:
    return Message.from_dict(d) if isinstance(d, dict) else None


# ── Connection ────────────────────────────────────────────────────────────────

@dataclass
class ReadyEvent:
    """user:authenticated — fired once after login."""
    user: User
    servers: list[Server] = field(default_factory=list)
    channels: list[Channel] = field(default_factory=list)
    members: list[Member] = field(default_factory=list)
    roles: list[Role] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "ReadyEvent":
        return cls(
            user=User.from_dict(d["user"]),
            servers=[Server.from_dict(s) for s in d.get("servers", [])],
            channels=[Channel.from_dict(c) for c in d.get("channels", [])],
            members=[Member.from_dict(m) for m in d.get("serverMembers", [])],
            roles=[Role.from_dict(r) for r in d.get("serverRoles", [])],
        )


# ── Messages ──────────────────────────────────────────────────────────────────

@dataclass
class MessageCreatedEvent:
    """message:created"""
    message: Message
    socket_id: str = ""
    server_id: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "MessageCreatedEvent":
        msg_data = d.get("message", d)
        if "serverId" not in msg_data and "serverId" in d:
            msg_data = {**msg_data, "serverId": d["serverId"]}
        return cls(
            message=Message.from_dict(msg_data),
            socket_id=d.get("socketId", ""),
            server_id=d.get("serverId"),
        )


@dataclass
class MessageUpdatedEvent:
    """message:updated"""
    channel_id: str
    message_id: str
    updated: dict  # partial fields

    @classmethod
    def from_dict(cls, d: dict) -> "MessageUpdatedEvent":
        return cls(
            channel_id=d["channelId"],
            message_id=d["messageId"],
            updated=d.get("updated", {}),
        )


@dataclass
class MessageDeletedEvent:
    """message:deleted"""
    channel_id: str
    message_id: str
    deleted_attachment_count: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "MessageDeletedEvent":
        return cls(
            channel_id=d["channelId"],
            message_id=d["messageId"],
            deleted_attachment_count=d.get("deletedAttachmentCount", 0),
        )


@dataclass
class ReactionAddedEvent:
    """message:reaction_added"""
    message_id: str
    channel_id: str
    count: int
    reacted_by_user_id: str
    name: str
    emoji_id: Optional[str] = None
    gif: bool = False
    webp: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "ReactionAddedEvent":
        return cls(
            message_id=d["messageId"],
            channel_id=d["channelId"],
            count=d["count"],
            reacted_by_user_id=d["reactedByUserId"],
            name=d["name"],
            emoji_id=d.get("emojiId"),
            gif=d.get("gif", False),
            webp=d.get("webp", False),
        )


@dataclass
class ReactionRemovedEvent:
    """message:reaction_removed"""
    message_id: str
    channel_id: str
    count: int
    removed_by_user_id: str
    name: str
    emoji_id: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "ReactionRemovedEvent":
        return cls(
            message_id=d["messageId"],
            channel_id=d["channelId"],
            count=d["count"],
            removed_by_user_id=d["reactionRemovedByUserId"],
            name=d["name"],
            emoji_id=d.get("emojiId"),
        )


# ── Server ────────────────────────────────────────────────────────────────────

@dataclass
class ServerUpdatedEvent:
    """server:updated"""
    server_id: str
    updated: dict

    @classmethod
    def from_dict(cls, d: dict) -> "ServerUpdatedEvent":
        return cls(server_id=d.get("serverId", d.get("id", "")), updated=d)


@dataclass
class MemberJoinedEvent:
    """server:member_joined"""
    member: Member
    server_id: str

    @classmethod
    def from_dict(cls, d: dict) -> "MemberJoinedEvent":
        return cls(member=Member.from_dict(d), server_id=d.get("serverId", ""))


@dataclass
class MemberLeftEvent:
    """server:member_left"""
    server_id: str
    user_id: str

    @classmethod
    def from_dict(cls, d: dict) -> "MemberLeftEvent":
        return cls(server_id=d.get("serverId", ""), user_id=d.get("userId", ""))


@dataclass
class MemberUpdatedEvent:
    """server:member_updated"""
    server_id: str
    user_id: str
    updated: dict

    @classmethod
    def from_dict(cls, d: dict) -> "MemberUpdatedEvent":
        return cls(
            server_id=d.get("serverId", ""),
            user_id=d.get("userId", ""),
            updated=d,
        )


@dataclass
class ChannelCreatedEvent:
    """server:channel_created"""
    channel: Channel

    @classmethod
    def from_dict(cls, d: dict) -> "ChannelCreatedEvent":
        return cls(channel=Channel.from_dict(d))


@dataclass
class ChannelUpdatedEvent:
    """server:channel_updated"""
    channel_id: str
    updated: dict

    @classmethod
    def from_dict(cls, d: dict) -> "ChannelUpdatedEvent":
        return cls(channel_id=d.get("id", d.get("channelId", "")), updated=d)


@dataclass
class ChannelDeletedEvent:
    """server:channel_deleted"""
    channel_id: str
    server_id: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "ChannelDeletedEvent":
        return cls(channel_id=d.get("channelId", d.get("id", "")), server_id=d.get("serverId"))


@dataclass
class RoleCreatedEvent:
    """server:role_created"""
    role: Role

    @classmethod
    def from_dict(cls, d: dict) -> "RoleCreatedEvent":
        return cls(role=Role.from_dict(d))


@dataclass
class RoleUpdatedEvent:
    """server:role_updated"""
    role_id: str
    server_id: str
    updated: dict

    @classmethod
    def from_dict(cls, d: dict) -> "RoleUpdatedEvent":
        return cls(
            role_id=d.get("id", d.get("roleId", "")),
            server_id=d.get("serverId", ""),
            updated=d,
        )


@dataclass
class RoleDeletedEvent:
    """server:role_deleted"""
    role_id: str
    server_id: str

    @classmethod
    def from_dict(cls, d: dict) -> "RoleDeletedEvent":
        return cls(role_id=d.get("roleId", d.get("id", "")), server_id=d.get("serverId", ""))


# ── Presence ──────────────────────────────────────────────────────────────────

@dataclass
class PresenceUpdatedEvent:
    """user:presence_update"""
    user_id: str
    status: int
    custom: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "PresenceUpdatedEvent":
        return cls(
            user_id=d.get("userId", ""),
            status=d.get("status", 0),
            custom=d.get("custom"),
        )


@dataclass
class TypingEvent:
    """channel:typing"""
    channel_id: str
    user_id: str
    server_id: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "TypingEvent":
        return cls(
            channel_id=d.get("channelId", ""),
            user_id=d.get("userId", ""),
            server_id=d.get("serverId"),
        )


# ── Dispatch map: event name → deserializer ───────────────────────────────────

EVENT_DESERIALIZERS: dict[str, type] = {
    "user:authenticated": ReadyEvent,
    "message:created": MessageCreatedEvent,
    "message:updated": MessageUpdatedEvent,
    "message:deleted": MessageDeletedEvent,
    "message:reaction_added": ReactionAddedEvent,
    "message:reaction_removed": ReactionRemovedEvent,
    "server:updated": ServerUpdatedEvent,
    "server:member_joined": MemberJoinedEvent,
    "server:member_left": MemberLeftEvent,
    "server:member_updated": MemberUpdatedEvent,
    "server:channel_created": ChannelCreatedEvent,
    "server:channel_updated": ChannelUpdatedEvent,
    "server:channel_deleted": ChannelDeletedEvent,
    "server:role_created": RoleCreatedEvent,
    "server:role_updated": RoleUpdatedEvent,
    "server:role_deleted": RoleDeletedEvent,
    "user:presence_update": PresenceUpdatedEvent,
    "channel:typing": TypingEvent,
}


def deserialize(event: str, data: Any) -> Any:
    """Return a typed event object if a deserializer exists, else return data as-is."""
    cls = EVENT_DESERIALIZERS.get(event)
    if cls and isinstance(data, dict):
        try:
            return cls.from_dict(data)
        except Exception:
            pass  # fall back to raw dict on malformed payloads
    return data
