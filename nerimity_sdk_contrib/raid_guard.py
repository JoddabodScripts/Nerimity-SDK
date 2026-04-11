"""RaidGuardPlugin — automatic lockdown on member-join spike.

Monitors the rate of ``member:joined`` events.  If more than *threshold*
members join within *window* seconds the server is considered under a raid
and the bot posts a lockdown alert to the configured channel.

Lockdown mode can be cleared manually with ``/raidguard unlock``.

Commands
--------
``/raidguard status``  — show current guard status and join rate.
``/raidguard unlock``  — manually clear lockdown (mod only).
``/raidguard lock``    — manually trigger lockdown (mod only).

Usage::

    await bot.plugins.load(RaidGuardPlugin(
        alert_channel_id="123456789",
        threshold=10,       # joins in …
        window=30.0,        # … this many seconds triggers lockdown
        mod_role_ids=["111222333"],
    ))
"""
from __future__ import annotations

import asyncio
import time
from collections import deque

from nerimity_sdk.plugins.manager import PluginBase, listener


class RaidGuardPlugin(PluginBase):
    """Detects and alerts on member-join spikes."""
    name = "raid_guard"

    def __init__(
        self,
        alert_channel_id: str,
        threshold: int = 10,
        window: float = 30.0,
        mod_role_ids: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.alert_channel_id = alert_channel_id
        self.threshold = threshold
        self.window = window
        self.mod_role_ids: set[str] = set(mod_role_ids or [])

        self._join_times: deque[float] = deque()
        self._locked: bool = False

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _is_mod(self, ctx) -> bool:
        if not self.mod_role_ids:
            return True
        member = ctx.member
        if member is None:
            return False
        return bool(self.mod_role_ids.intersection(getattr(member, "role_ids", [])))

    def _current_rate(self) -> int:
        """Number of joins in the last *window* seconds."""
        cutoff = time.monotonic() - self.window
        while self._join_times and self._join_times[0] < cutoff:
            self._join_times.popleft()
        return len(self._join_times)

    # ── Member join listener ──────────────────────────────────────────────────

    @listener("member:joined")
    async def on_member_join(self, event) -> None:
        from nerimity_sdk.events.payloads import MemberJoinedEvent
        if not isinstance(event, MemberJoinedEvent):
            return

        self._join_times.append(time.monotonic())
        rate = self._current_rate()

        if not self._locked and rate >= self.threshold:
            self._locked = True
            await self.bot.rest.create_message(
                self.alert_channel_id,
                f"🚨 **RAID ALERT** — {rate} members joined in the last "
                f"{self.window:.0f}s (threshold: {self.threshold}).\n"
                f"Use `/raidguard unlock` to clear lockdown once the raid is over."
            )

    # ── Commands ──────────────────────────────────────────────────────────────

    async def on_load(self) -> None:
        plugin = self

        @self.bot.command("raidguard", description="Raid guard status and controls")
        async def raidguard_cmd(ctx) -> None:
            sub = (ctx.args[0].lower() if ctx.args else "status")

            if sub == "status":
                rate = plugin._current_rate()
                status = "🔴 LOCKED DOWN" if plugin._locked else "🟢 Normal"
                await ctx.reply(
                    f"**Raid Guard** — {status}\n"
                    f"Joins in last {plugin.window:.0f}s: **{rate}** (threshold: {plugin.threshold})"
                )

            elif sub == "unlock":
                if not plugin._is_mod(ctx):
                    return await ctx.reply("❌ You don't have permission to unlock.")
                plugin._locked = False
                plugin._join_times.clear()
                await ctx.reply("✅ Lockdown cleared. Raid guard reset.")

            elif sub == "lock":
                if not plugin._is_mod(ctx):
                    return await ctx.reply("❌ You don't have permission to trigger lockdown.")
                plugin._locked = True
                await ctx.reply("🔒 Lockdown manually activated.")

            else:
                await ctx.reply("Usage: `/raidguard [status|lock|unlock]`")
