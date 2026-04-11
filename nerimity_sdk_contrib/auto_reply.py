"""AutoReplyPlugin — keyword-triggered auto-replies."""
from __future__ import annotations
import re
from nerimity_sdk.plugins.manager import PluginBase, listener


class AutoReplyPlugin(PluginBase):
    """Automatically reply when a message contains a keyword or matches a regex.

    Usage::

        await bot.plugins.load(AutoReplyPlugin(rules=[
            ("thanks", "You're welcome! 😊"),
            (r"good (morning|day)", "Good day to you too! ☀️"),
        ]))
    """

    name = "auto_reply"
    description = "Keyword-triggered auto-replies"

    def __init__(self, rules: list[tuple[str, str]] | None = None) -> None:
        super().__init__()
        # Each rule: (pattern, response) — pattern is treated as regex
        self._rules: list[tuple[re.Pattern, str]] = [
            (re.compile(p, re.IGNORECASE), r) for p, r in (rules or [])
        ]

    def add_rule(self, pattern: str, response: str) -> None:
        self._rules.append((re.compile(pattern, re.IGNORECASE), response))

    @listener("message:created")
    async def _on_message(self, event) -> None:
        from nerimity_sdk.events.payloads import MessageCreatedEvent
        msg = event.message if isinstance(event, MessageCreatedEvent) else None
        if not msg or not msg.content:
            return
        # Don't reply to bot's own messages
        if self.bot._me and msg.created_by.id == self.bot._me.id:
            return
        for pattern, response in self._rules:
            if pattern.search(msg.content):
                await self.bot.rest.create_message(msg.channel_id, response)
                break  # only first match
