"""GiveawayPlugin — react to enter, random winner picked after duration.

Usage::

    await bot.plugins.load(GiveawayPlugin())

Then::

    @bot.command("giveaway")
    async def giveaway(ctx):
        await ctx.bot_plugins["giveaway"].start(
            ctx, prize="Nitro", duration=60, emoji="🎉"
        )
"""
from __future__ import annotations
import asyncio
import random
from nerimity_sdk.plugins.manager import PluginBase, listener


class GiveawayPlugin(PluginBase):
    name = "giveaway"

    def __init__(self) -> None:
        super().__init__()
        # message_id → set of user_ids
        self._entries: dict[str, set[str]] = {}

    async def start(self, ctx, prize: str, duration: int = 60,
                    emoji: str = "🎉") -> None:
        msg = await ctx.reply(
            f"{emoji} **GIVEAWAY** {emoji}\n"
            f"Prize: **{prize}**\n"
            f"React with {emoji} to enter! Ends in {duration}s."
        )
        self._entries[msg.id] = set()
        await self.bot.rest.add_reaction(msg.channel_id, msg.id, emoji)
        await asyncio.sleep(duration)

        entries = self._entries.pop(msg.id, set())
        if not entries:
            await self.bot.rest.create_message(msg.channel_id,
                f"{emoji} Giveaway for **{prize}** ended — no entries!")
            return
        winner = random.choice(list(entries))
        from nerimity_sdk.utils.mentions import mention
        await self.bot.rest.create_message(
            msg.channel_id,
            f"{emoji} Giveaway ended! **{prize}** goes to {mention(winner)}! Congratulations!"
        )

    @listener("message:reaction_added")
    async def on_react(self, event) -> None:
        from nerimity_sdk.events.payloads import ReactionAddedEvent
        if not isinstance(event, ReactionAddedEvent):
            return
        if event.message_id in self._entries:
            self._entries[event.message_id].add(event.user_id)

    @listener("message:reaction_removed")
    async def on_unreact(self, event) -> None:
        from nerimity_sdk.events.payloads import ReactionRemovedEvent
        if not isinstance(event, ReactionRemovedEvent):
            return
        if event.message_id in self._entries:
            self._entries[event.message_id].discard(event.user_id)
