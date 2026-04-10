"""ReminderPlugin — !remind 10m take a break → DMs the user after the time.

Usage::

    await bot.plugins.load(ReminderPlugin())

    @bot.command("remind", description="Set a reminder")
    async def remind(ctx):
        # ctx.args[0] = time string (e.g. 10m, 2h, 30s)
        # ctx.args[1:] = reminder text
        await ctx.bot_plugins["reminders"].set(ctx)
"""
from __future__ import annotations
import asyncio
import re
from nerimity_sdk.plugins.manager import PluginBase


def _parse_duration(s: str) -> float:
    """Parse '10m', '2h', '30s', '1h30m' into seconds."""
    total = 0.0
    for value, unit in re.findall(r"(\d+)([smhd])", s.lower()):
        total += int(value) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return total or float(s)  # fallback: treat as raw seconds


class ReminderPlugin(PluginBase):
    name = "reminders"

    async def set(self, ctx) -> None:
        if not ctx.args:
            await ctx.reply("Usage: /remind <time> <message>  e.g. /remind 10m take a break")
            return
        try:
            delay = _parse_duration(ctx.args[0])
        except (ValueError, KeyError):
            await ctx.reply("Invalid time format. Use e.g. `30s`, `10m`, `2h`.")
            return
        text = " ".join(ctx.args[1:]) or "Your reminder!"
        await ctx.reply(f"⏰ Got it! I'll remind you in {ctx.args[0]}: *{text}*")
        user_id = ctx.author.id
        asyncio.create_task(self._fire(user_id, delay, text))

    async def _fire(self, user_id: str, delay: float, text: str) -> None:
        await asyncio.sleep(delay)
        try:
            channel_data = await self.bot.rest.open_dm(user_id)
            await self.bot.rest.create_message(channel_data["id"], f"⏰ Reminder: {text}")
        except Exception as exc:
            self.bot.logger.error(f"[Reminders] Failed to send reminder: {exc}")
