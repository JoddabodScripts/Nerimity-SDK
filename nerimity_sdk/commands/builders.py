"""Fluent builder API for messages and embeds.

Usage::

    msg = MessageBuilder().content("hello").reply_to("msg_id").build()
    embed = Embed().title("Info").description("Some text").color(0x5865F2)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from nerimity_sdk.transport.rest import RESTClient
    from nerimity_sdk.models import Message


@dataclass
class Embed:
    """Fluent builder for a Nerimity message embed (OG-style)."""
    _title: Optional[str] = field(default=None, repr=False)
    _description: Optional[str] = field(default=None, repr=False)
    _url: Optional[str] = field(default=None, repr=False)
    _image_url: Optional[str] = field(default=None, repr=False)
    _color: Optional[str] = field(default=None, repr=False)  # hex string

    def title(self, value: str) -> "Embed":
        self._title = value
        return self

    def description(self, value: str) -> "Embed":
        self._description = value
        return self

    def url(self, value: str) -> "Embed":
        self._url = value
        return self

    def image(self, url: str) -> "Embed":
        self._image_url = url
        return self

    def color(self, value: int | str) -> "Embed":
        if isinstance(value, int):
            self._color = f"#{value:06x}"
        else:
            self._color = value
        return self

    def to_dict(self) -> dict:
        d: dict = {}
        if self._title:
            d["title"] = self._title
        if self._description:
            d["description"] = self._description
        if self._url:
            d["url"] = self._url
        if self._image_url:
            d["imageUrl"] = self._image_url
        if self._color:
            d["hexColor"] = self._color
        return d


class MessageBuilder:
    """Fluent builder for sending a Nerimity message."""

    def __init__(self) -> None:
        self._content: Optional[str] = None
        self._reply_to: list[str] = []
        self._mention_replies: bool = True
        self._silent: bool = False
        self._file_id: Optional[str] = None
        self._socket_id: Optional[str] = None

    def content(self, text: str) -> "MessageBuilder":
        self._content = text
        return self

    def reply_to(self, *message_ids: str, mention: bool = True) -> "MessageBuilder":
        self._reply_to.extend(message_ids)
        self._mention_replies = mention
        return self

    def silent(self, value: bool = True) -> "MessageBuilder":
        self._silent = value
        return self

    def attach(self, nerimity_file_id: str) -> "MessageBuilder":
        self._file_id = nerimity_file_id
        return self

    def socket_id(self, sid: str) -> "MessageBuilder":
        self._socket_id = sid
        return self

    def build(self) -> dict:
        body: dict = {}
        if self._content:
            body["content"] = self._content
        if self._reply_to:
            body["replyToMessageIds"] = self._reply_to
            body["mentionReplies"] = self._mention_replies
        if self._silent:
            body["silent"] = True
        if self._file_id:
            body["nerimityCdnFileId"] = self._file_id
        if self._socket_id:
            body["socketId"] = self._socket_id
        return body

    async def send(self, rest: "RESTClient", channel_id: str) -> "Message":
        from nerimity_sdk.models import Message
        data = await rest.request("POST", f"/channels/{channel_id}/messages", json=self.build())
        return Message.from_dict(data)
