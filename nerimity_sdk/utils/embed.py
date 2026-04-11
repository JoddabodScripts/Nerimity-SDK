"""Fluent Embed builder for Nerimity messages."""
from __future__ import annotations
from typing import Optional


class Embed:
    """Build a rich embed message with a fluent interface.

    Usage::

        embed = (
            Embed()
            .title("Hello!")
            .description("This is an embed.")
            .color("#a78bfa")
            .field("Score", "100", inline=True)
            .field("Rank", "#1", inline=True)
            .footer("Powered by nerimity-sdk")
        )
        await ctx.reply_embed(embed)
    """

    def __init__(self) -> None:
        self._data: dict = {}

    def title(self, text: str) -> "Embed":
        self._data["title"] = text
        return self

    def description(self, text: str) -> "Embed":
        self._data["description"] = text
        return self

    def color(self, hex_color: str) -> "Embed":
        self._data["color"] = hex_color.lstrip("#")
        return self

    def url(self, href: str) -> "Embed":
        self._data["url"] = href
        return self

    def image(self, url: str) -> "Embed":
        self._data["image"] = {"url": url}
        return self

    def thumbnail(self, url: str) -> "Embed":
        self._data["thumbnail"] = {"url": url}
        return self

    def author(self, name: str, icon_url: Optional[str] = None,
               url: Optional[str] = None) -> "Embed":
        a: dict = {"name": name}
        if icon_url:
            a["iconUrl"] = icon_url
        if url:
            a["url"] = url
        self._data["author"] = a
        return self

    def footer(self, text: str, icon_url: Optional[str] = None) -> "Embed":
        f: dict = {"text": text}
        if icon_url:
            f["iconUrl"] = icon_url
        self._data["footer"] = f
        return self

    def field(self, name: str, value: str, inline: bool = False) -> "Embed":
        self._data.setdefault("fields", []).append(
            {"name": name, "value": value, "inline": inline}
        )
        return self

    def to_dict(self) -> dict:
        return dict(self._data)
