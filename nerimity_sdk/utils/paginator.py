"""Paginator: send multi-page responses with prev/next button navigation."""
from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from nerimity_sdk.context.ctx import Context
    from nerimity_sdk.commands.buttons import ButtonRouter


class Paginator:
    """
    Usage::

        pages = ["Page 1 content", "Page 2 content", "Page 3 content"]
        await Paginator(pages).send(ctx)

    With a custom timeout (seconds before buttons stop responding)::

        await Paginator(pages, timeout=120).send(ctx)
    """

    def __init__(self, pages: list[str], timeout: float = 60.0) -> None:
        if not pages:
            raise ValueError("Paginator requires at least one page")
        self.pages = pages
        self.timeout = timeout
        self._index = 0

    def _render(self) -> str:
        total = len(self.pages)
        header = f"[{self._index + 1}/{total}]" if total > 1 else ""
        return f"{header}\n{self.pages[self._index]}".strip()

    def _button_ids(self, msg_id: str) -> tuple[str, str]:
        return f"page:prev:{msg_id}", f"page:next:{msg_id}"

    async def send(self, ctx: "Context") -> None:
        from nerimity_sdk.commands.builders import MessageBuilder
        from nerimity_sdk.commands.buttons import Button, ComponentRow, ButtonContext

        # Send initial page (plain text — Nerimity button API via message body)
        sent = await ctx.reply(self._render())
        if len(self.pages) == 1:
            return

        msg_id = sent.id
        prev_id, next_id = self._button_ids(msg_id)

        # Register ephemeral button handlers on the bot's ButtonRouter
        bot_router: Optional["ButtonRouter"] = getattr(ctx, "_button_router", None)
        if bot_router is None:
            # No button router wired — fall back to ask()-based navigation
            await self._ask_navigation(ctx)
            return

        async def on_prev(bctx: ButtonContext) -> None:
            if self._index > 0:
                self._index -= 1
            await bctx.update_message(self._render())

        async def on_next(bctx: ButtonContext) -> None:
            if self._index < len(self.pages) - 1:
                self._index += 1
            await bctx.update_message(self._render())

        bot_router.register(prev_id, on_prev, ttl=self.timeout)
        bot_router.register(next_id, on_next, ttl=self.timeout)

    async def _ask_navigation(self, ctx: "Context") -> None:
        """Fallback: text-based prev/next when no ButtonRouter is available."""
        total = len(self.pages)
        while True:
            nav = f"\nType `next`, `prev`, or `stop` ({self._index + 1}/{total})"
            response = await ctx.ask(nav, timeout=self.timeout)
            if response is None:
                break
            cmd = response.content.strip().lower()
            if cmd == "next" and self._index < total - 1:
                self._index += 1
            elif cmd == "prev" and self._index > 0:
                self._index -= 1
            elif cmd == "stop":
                break
            await ctx.reply(self._render())
