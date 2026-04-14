"""Fluent Embed builder for Nerimity messages."""
from __future__ import annotations
from typing import Optional
import html as _html


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
        self._title: Optional[str] = None
        self._description: Optional[str] = None
        self._color: Optional[str] = None
        self._url: Optional[str] = None
        self._image: Optional[str] = None
        self._thumbnail: Optional[str] = None
        self._footer: Optional[str] = None
        self._author: Optional[str] = None
        self._fields: list[dict] = []

    def title(self, text: str) -> "Embed":
        self._title = text
        return self

    def description(self, text: str) -> "Embed":
        self._description = text
        return self

    def color(self, hex_color: str) -> "Embed":
        self._color = hex_color if hex_color.startswith("#") else f"#{hex_color}"
        return self

    def url(self, href: str) -> "Embed":
        self._url = href
        return self

    def image(self, url: str) -> "Embed":
        self._image = url
        return self

    def thumbnail(self, url: str) -> "Embed":
        self._thumbnail = url
        return self

    def author(self, name: str, icon_url: Optional[str] = None,
               url: Optional[str] = None) -> "Embed":
        self._author = name
        return self

    def footer(self, text: str, icon_url: Optional[str] = None) -> "Embed":
        self._footer = text
        return self

    def field(self, name: str, value: str, inline: bool = False) -> "Embed":
        self._fields.append({"name": name, "value": value, "inline": inline})
        return self

    def to_html(self) -> str:
        """Render the embed as an HTML string for the Nerimity htmlEmbed API field."""
        e = _html.escape
        border = f"border:4px solid {self._color};" if self._color else ""
        parts = [f'<div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:4px;{border}max-width:520px">']

        if self._author:
            parts.append(f'<div style="font-size:12px;opacity:0.7;margin-bottom:4px">{e(self._author)}</div>')

        if self._title:
            if self._url:
                parts.append(f'<div style="font-weight:700;margin-bottom:4px"><a href="{e(self._url)}" style="color:inherit">{e(self._title)}</a></div>')
            else:
                parts.append(f'<div style="font-weight:700;margin-bottom:4px">{e(self._title)}</div>')

        if self._description:
            parts.append(f'<div style="font-size:14px;margin-bottom:8px">{e(self._description)}</div>')

        if self._fields:
            parts.append('<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px">')
            for f in self._fields:
                width = "calc(33% - 8px)" if f["inline"] else "100%"
                parts.append(
                    f'<div style="min-width:80px;width:{width}">'
                    f'<div style="font-size:12px;font-weight:700">{e(f["name"])}</div>'
                    f'<div style="font-size:14px">{e(f["value"])}</div>'
                    f'</div>'
                )
            parts.append('</div>')

        if self._image:
            parts.append(f'<img src="{e(self._image)}" style="max-width:100%;border-radius:4px;margin-bottom:8px" />')

        if self._footer:
            parts.append(f'<div style="font-size:11px;opacity:0.6">{e(self._footer)}</div>')

        parts.append('</div>')
        return "".join(parts)

    # Keep to_dict for backwards compat (returns htmlEmbed-ready dict)
    def to_dict(self) -> dict:
        return {"htmlEmbed": self.to_html()}
