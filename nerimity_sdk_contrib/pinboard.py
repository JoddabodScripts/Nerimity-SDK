"""PinboardPlugin — community-driven message pinboard.

Any member can nominate a message for the pinboard by reacting with the
configured emoji (default 📌).  Once a message reaches *threshold* reactions
it is forwarded to the pinboard channel.  Each message is only pinned once.

Commands
--------
``/pinboard``  — show the last 5 pinned messages.

Usage::

    await bot.plugins.load(PinboardPlugin(
        channel_id="123456789",   # where pinned messages are posted
        threshold=3,              # reactions needed
        emoji="📌",
    ))
"""
from __future__ import annotations

from nerimity_sdk.plugins.manager import PluginBase, listener


class PinboardPlugin(PluginBase):
    """Community pinboard driven by reaction threshold."""
    name = "pinboard"

    def __init__(
        self,
        channel_id: str,
        threshold: int = 3,
        emoji: str = "📌",
    ) -> None:
        super().__init__()
        self.channel_id = channel_id
        self.threshold = threshold
        self.emoji = emoji

    # ── Store helpers ─────────────────────────────────────────────────────────

    def _pinned_key(self, server_id: str, message_id: str) -> str:
        return f"pinboard:pinned:{server_id}:{message_id}"

    def _log_key(self, server_id: str) -> str:
        return f"pinboard:log:{server_id}"

    # ── Reaction listener ─────────────────────────────────────────────────────

    @listener("reaction:added")
    async def on_reaction(self, event) -> None:
        from nerimity_sdk.events.payloads import ReactionAddedEvent
        if not isinstance(event, ReactionAddedEvent):
            return

        reaction = event.reaction
        if getattr(reaction, "name", None) != self.emoji:
            return

        server_id = getattr(reaction, "server_id", None)
        message_id = str(reaction.message_id)
        channel_id = str(reaction.channel_id)

        if not server_id:
            return

        # Already pinned?
        if await self.bot.store.get(self._pinned_key(server_id, message_id)):
            return

        # Count reactions on the message
        count = getattr(reaction, "count", 1)
        if count < self.threshold:
            return

        # Mark as pinned before fetching to avoid races
        await self.bot.store.set(self._pinned_key(server_id, message_id), "1")

        # Fetch the original message
        try:
            msg_data = await self.bot.rest.get_message(channel_id, message_id)
        except Exception:
            return

        author = msg_data.get("createdBy", {})
        username = author.get("username", "Unknown")
        content = msg_data.get("content", "")
        jump = f"https://nerimity.com/app/servers/{server_id}/channels/{channel_id}/{message_id}"

        text = (
            f"{self.emoji} **Pinned from** <#{channel_id}> by **{username}**\n"
            f"{content}\n"
            f"[Jump to message]({jump})"
        )
        await self.bot.rest.create_message(self.channel_id, text)

        # Append to log (keep last 20)
        log = await self.bot.store.get(self._log_key(server_id))
        entries: list[dict] = log if isinstance(log, list) else []
        entries.append({"message_id": message_id, "channel_id": channel_id, "author": username, "content": content[:100]})
        await self.bot.store.set(self._log_key(server_id), entries[-20:])

    # ── Command ───────────────────────────────────────────────────────────────

    async def on_load(self) -> None:
        plugin = self

        @self.bot.command("pinboard", description="Show recently pinned messages")
        async def pinboard_cmd(ctx) -> None:
            if not ctx.server_id:
                return await ctx.reply("❌ Pinboard only works in a server.")
            log = await plugin.bot.store.get(plugin._log_key(ctx.server_id))
            entries: list[dict] = log if isinstance(log, list) else []
            if not entries:
                return await ctx.reply("No messages have been pinned yet.")
            lines = [f"{plugin.emoji} **Recent Pins**"]
            for e in reversed(entries[-5:]):
                preview = e["content"][:60] + ("…" if len(e["content"]) > 60 else "")
                lines.append(f"• **{e['author']}**: {preview}")
            await ctx.reply("\n".join(lines))
