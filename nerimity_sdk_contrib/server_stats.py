"""ServerStatsPlugin — post periodic server stats to a channel."""
from __future__ import annotations
from nerimity_sdk.plugins.manager import PluginBase


class ServerStatsPlugin(PluginBase):
    """Posts bot + server stats to a channel on a schedule.

    Usage::

        await bot.plugins.load(ServerStatsPlugin(
            channel_id="YOUR_CHANNEL_ID",
            cron="0 * * * *",   # every hour
        ))
    """

    name = "server_stats"
    description = "Periodic server stats posts"

    def __init__(self, channel_id: str, cron: str = "0 * * * *") -> None:
        super().__init__()
        self._channel_id = channel_id
        self._cron = cron

    async def on_ready(self) -> None:
        @self.bot.cron(self._cron)
        async def _post_stats():
            s = self.bot.stats
            up = s["uptime_seconds"]
            h, rem = divmod(int(up), 3600)
            m, sec = divmod(rem, 60)
            await self.bot.rest.create_message(
                self._channel_id,
                f"📊 **Server Stats**\n"
                f"⏱ Uptime: `{h:02d}:{m:02d}:{sec:02d}`\n"
                f"💬 Messages seen: `{s['messages_seen']}`\n"
                f"⚡ Commands run: `{s['commands_dispatched']}`\n"
                f"👥 Cached members: `{s['cached_members']}`\n"
                f"🚦 Rate limit hits: `{s['rate_limit_hits']}`"
            )
