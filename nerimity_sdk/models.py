"""Typed data models for Nerimity API objects."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntFlag
from typing import Any, Optional


class UserBadge(IntFlag):
    NONE = 0
    FOUNDER = 1
    ADMIN = 2
    CONTRIBUTOR = 4
    SUPPORTER = 8


class Permissions(IntFlag):
    NONE = 0
    ADMIN = 1
    SEND_MESSAGES = 2
    MANAGE_ROLES = 4
    KICK_MEMBERS = 8
    BAN_MEMBERS = 16
    MANAGE_CHANNELS = 32
    MANAGE_SERVER = 64


@dataclass
class User:
    id: str
    username: str
    tag: str
    hex_color: str
    badge: UserBadge = UserBadge.NONE
    avatar: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "User":
        return cls(
            id=d["id"],
            username=d["username"],
            tag=d["tag"],
            hex_color=d.get("hexColor", ""),
            badge=UserBadge(d.get("badge", 0)),
            avatar=d.get("avatar"),
        )

    def merge(self, d: dict) -> None:
        """Merge partial update into this object."""
        if "username" in d:
            self.username = d["username"]
        if "tag" in d:
            self.tag = d["tag"]
        if "hexColor" in d:
            self.hex_color = d["hexColor"]
        if "badge" in d:
            self.badge = UserBadge(d["badge"])
        if "avatar" in d:
            self.avatar = d["avatar"]


@dataclass
class Role:
    id: str
    server_id: str
    created_by_id: str
    order: int
    bot_role: bool
    hex_color: str
    name: str
    hide_role: bool
    created_at: str
    permissions: Permissions = Permissions.NONE

    @classmethod
    def from_dict(cls, d: dict) -> "Role":
        return cls(
            id=d["id"],
            server_id=d["serverId"],
            created_by_id=d["createdById"],
            order=d["order"],
            bot_role=d.get("botRole", False),
            hex_color=d.get("hexColor", ""),
            name=d["name"],
            hide_role=d.get("hideRole", False),
            created_at=d.get("createdAt", ""),
            permissions=Permissions(d.get("permissions", 0)),
        )

    def merge(self, d: dict) -> None:
        for key, attr in [("name", "name"), ("hexColor", "hex_color"),
                          ("hideRole", "hide_role"), ("order", "order")]:
            if key in d:
                setattr(self, attr, d[key])
        if "permissions" in d:
            self.permissions = Permissions(d["permissions"])


@dataclass
class Channel:
    id: str
    server_id: Optional[str] = None
    name: Optional[str] = None
    type: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "Channel":
        return cls(
            id=d["id"],
            server_id=d.get("serverId"),
            name=d.get("name"),
            type=d.get("type", 0),
        )

    def merge(self, d: dict) -> None:
        if "name" in d:
            self.name = d["name"]


@dataclass
class Server:
    id: str
    name: str
    created_by_id: str
    hex_color: Optional[str] = None
    avatar: Optional[str] = None
    channels: dict[str, Channel] = field(default_factory=dict)
    roles: dict[str, Role] = field(default_factory=dict)
    members: dict[str, "Member"] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Server":
        srv = cls(
            id=d["id"],
            name=d["name"],
            created_by_id=d.get("createdById", ""),
            hex_color=d.get("hexColor"),
            avatar=d.get("avatar"),
        )
        for ch in d.get("channels", []):
            c = Channel.from_dict(ch)
            srv.channels[c.id] = c
        for r in d.get("roles", []):
            role = Role.from_dict(r)
            srv.roles[role.id] = role
        for m in d.get("members", []):
            member = Member.from_dict(m)
            srv.members[member.user.id] = member
        return srv

    def merge(self, d: dict) -> None:
        if "name" in d:
            self.name = d["name"]
        if "hexColor" in d:
            self.hex_color = d["hexColor"]
        if "avatar" in d:
            self.avatar = d["avatar"]


@dataclass
class Member:
    user: User
    server_id: str
    role_ids: list[str] = field(default_factory=list)
    joined_at: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "Member":
        return cls(
            user=User.from_dict(d["user"]) if isinstance(d.get("user"), dict) else User(
                id=d.get("userId", ""), username="", tag="", hex_color=""
            ),
            server_id=d.get("serverId", ""),
            role_ids=d.get("roleIds", []),
            joined_at=d.get("joinedAt"),
        )


@dataclass
class MessageAttachment:
    id: str
    file_id: str
    mime: str
    width: Optional[int] = None
    height: Optional[int] = None

    @classmethod
    def from_dict(cls, d: dict) -> "MessageAttachment":
        return cls(
            id=d.get("id", ""),
            file_id=d.get("fileId", ""),
            mime=d.get("mime", ""),
            width=d.get("width"),
            height=d.get("height"),
        )


@dataclass
class Message:
    id: str
    channel_id: str
    type: int
    content: str
    created_by: User
    created_at: int
    edited_at: Optional[int] = None
    reactions: list[Any] = field(default_factory=list)
    mentions: list[Any] = field(default_factory=list)
    embed: Optional[dict] = None
    attachments: list[MessageAttachment] = field(default_factory=list)
    server_id: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "Message":
        return cls(
            id=d["id"],
            channel_id=d["channelId"],
            type=d.get("type", 0),
            content=d.get("content", ""),
            created_by=User.from_dict(d["createdBy"]) if isinstance(d.get("createdBy"), dict) else User(
                id=d.get("createdBy", ""), username="", tag="", hex_color=""
            ),
            created_at=d.get("createdAt", 0),
            edited_at=d.get("editedAt"),
            reactions=d.get("reactions", []),
            mentions=d.get("mentions", []),
            embed=d.get("embed"),
            attachments=[MessageAttachment.from_dict(a) for a in d.get("attachments", [])],
            server_id=d.get("serverId"),
        )


@dataclass
class BotCommand:
    name: str
    description: Optional[str] = None
    args: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {"name": self.name}
        if self.description:
            d["description"] = self.description
        if self.args:
            d["args"] = self.args
        return d
