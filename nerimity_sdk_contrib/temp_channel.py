"""TempChannelPlugin — create temporary channels that auto-delete after inactivity."""
from __future__ import annotations
import asyncio
from nerimity_sdk.plugins.manager import PluginBase, listener


class TempChannelPlugin(PluginBase):
    """Creates temporary channels that delete themselves after inactivity.

    Usage::

        await bot.plugins.load(TempChannelPlugin(timeout=300))  # 5 min inactivity

    Users run /tempchannel <name> to create one.
    """

    name = "temp_channel"
    description = "Auto-deleting temporary channels"

    def __init__(self, timeout: float = 300.0) -> None:
        super().__init__()
        self._timeout = timeout
        # channel_id → asyncio.TimerHandle
        self._timers: dict[str, asyncio.Task] = {}

    async def on_load(self) -> None:
        @self.bot.command("tempchannel", description="Create a temporary channel",
                          usage="<name>", guild_only=True)
        async def tempchannel(ctx):
            if not ctx.args:
                return await ctx.reply("Usage: /tempchannel <name>")
            name = "-".join(ctx.args).lower()[:32]
            try:
                ch = await ctx.rest.create_channel(ctx.server_id, name)
                ch_id = ch["id"]
                await ctx.reply(f"✅ Created temporary channel <#{ch_id}>. It will be deleted after {int(self._timeout)}s of inactivity.")
                self._reset_timer(ch_id, ctx.server_id)
            except Exception as e:
                await ctx.reply(f"❌ Failed to create channel: {e}")

    def _reset_timer(self, channel_id: str, server_id: str) -> None:
        existing = self._timers.pop(channel_id, None)
        if existing:
            existing.cancel()

        async def _delete_after():
            await asyncio.sleep(self._timeout)
            try:
                await self.bot.rest.delete_channel(server_id, channel_id)
            except Exception:
                pass
            self._timers.pop(channel_id, None)

        self._timers[channel_id] = asyncio.create_task(_delete_after())

    @listener("message:created")
    async def _on_message(self, event) -> None:
        from nerimity_sdk.events.payloads import MessageCreatedEvent
        msg = event.message if isinstance(event, MessageCreatedEvent) else None
        if not msg:
            return
        if msg.channel_id in self._timers and msg.server_id:
            self._reset_timer(msg.channel_id, msg.server_id)
