"""LevelingPlugin — XP per message, level-up announcements.

Usage::

    await bot.plugins.load(LevelingPlugin(
        announce_channel_id="123",   # where to post level-up messages
        xp_per_message=10,
        xp_cooldown=60.0,            # seconds between XP grants per user
    ))

XP is stored in bot.store under "xp:{server_id}:{user_id}".
"""
from __future__ import annotations
import math
import time
from nerimity_sdk.plugins.manager import PluginBase, listener
from nerimity_sdk.utils.mentions import mention


def _level_for_xp(xp: int) -> int:
    """Level = floor(sqrt(xp / 100))"""
    return int(math.sqrt(xp / 100))


def _xp_for_level(level: int) -> int:
    return level * level * 100


class LevelingPlugin(PluginBase):
    """Grants XP for messages and announces level-ups."""
    name = "leveling"

    def __init__(self, announce_channel_id: str | None = None,
                 xp_per_message: int = 10, xp_cooldown: float = 60.0) -> None:
        super().__init__()
        self.announce_channel_id = announce_channel_id
        self.xp_per_message = int(xp_per_message)
        self.xp_cooldown = float(xp_cooldown)
        self._last_xp: dict[str, float] = {}  # "server:user" → monotonic time

    def _key(self, server_id: str, user_id: str) -> str:
        return f"xp:{server_id}:{user_id}"

    @listener("message:created")
    async def on_message(self, event) -> None:
        from nerimity_sdk.events.payloads import MessageCreatedEvent
        if not isinstance(event, MessageCreatedEvent):
            return
        msg = event.message
        if not msg.server_id:
            return

        uid = msg.created_by.id
        cooldown_key = f"{msg.server_id}:{uid}"
        now = time.monotonic()
        if now - self._last_xp.get(cooldown_key, 0) < self.xp_cooldown:
            return
        self._last_xp[cooldown_key] = now

        store_key = self._key(msg.server_id, uid)
        xp: int = int((await self.bot.store.get(store_key)) or 0)
        old_level = _level_for_xp(xp)
        xp += self.xp_per_message
        await self.bot.store.set(store_key, xp)
        new_level = _level_for_xp(xp)

        if new_level > old_level and self.announce_channel_id:
            await self.bot.rest.create_message(
                self.announce_channel_id,
                f"🎉 {mention(uid)} reached **level {new_level}**! "
                f"({xp} XP — next level at {_xp_for_level(new_level + 1)} XP)"
            )

    async def get_xp(self, server_id: str, user_id: str) -> int:
        return int((await self.bot.store.get(self._key(server_id, user_id))) or 0)

    async def get_level(self, server_id: str, user_id: str) -> int:
        return _level_for_xp(await self.get_xp(server_id, user_id))

    async def on_load(self) -> None:
        plugin = self

        @self.bot.command("level", description="Show your current level and XP")
        async def level_cmd(ctx):
            if not ctx.server_id:
                return await ctx.reply("This command only works in a server.")
            # Allow checking another user: /level @user
            target = ctx.mentions[0] if ctx.mentions else ctx.author
            xp = await plugin.get_xp(ctx.server_id, target.id)
            lvl = _level_for_xp(xp)
            next_xp = _xp_for_level(lvl + 1)
            needed = next_xp - xp
            bar_filled = int((xp - _xp_for_level(lvl)) / (next_xp - _xp_for_level(lvl)) * 10)
            bar = "█" * bar_filled + "░" * (10 - bar_filled)
            await ctx.reply(
                f"⭐ **{target.username}** — Level **{lvl}**\n"
                f"{bar} {xp} / {next_xp} XP\n"
                f"_{needed} XP to level {lvl + 1}_"
            )
