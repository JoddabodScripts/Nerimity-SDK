"""EconomyPlugin — virtual coin economy for your server.

Features
--------
- ``/balance [user]``   — check your (or another user's) coin balance.
- ``/daily``            — claim a daily reward (once per 24 h).
- ``/give <user> <amount>`` — transfer coins to another user.
- ``/richest``          — top-10 richest users in the server.

Coins are stored in the bot's store under ``eco:<server_id>:<user_id>``.

Usage::

    await bot.plugins.load(EconomyPlugin(
        daily_amount=100,
        currency_name="coins",
        currency_emoji="🪙",
    ))
"""
from __future__ import annotations

import time

from nerimity_sdk.plugins.manager import PluginBase
from nerimity_sdk.utils.mentions import mention


class EconomyPlugin(PluginBase):
    """Virtual coin economy."""
    name = "economy"

    def __init__(
        self,
        daily_amount: int = 100,
        currency_name: str = "coins",
        currency_emoji: str = "🪙",
        starting_balance: int = 0,
    ) -> None:
        super().__init__()
        self.daily_amount = daily_amount
        self.currency_name = currency_name
        self.currency_emoji = currency_emoji
        self.starting_balance = starting_balance

    # ── Store helpers ─────────────────────────────────────────────────────────

    def _bal_key(self, server_id: str, user_id: str) -> str:
        return f"eco:{server_id}:{user_id}"

    def _daily_key(self, server_id: str, user_id: str) -> str:
        return f"eco:daily:{server_id}:{user_id}"

    async def _get_balance(self, server_id: str, user_id: str) -> int:
        raw = await self.bot.store.get(self._bal_key(server_id, user_id))
        return int(raw) if raw is not None else self.starting_balance

    async def _set_balance(self, server_id: str, user_id: str, amount: int) -> None:
        await self.bot.store.set(self._bal_key(server_id, user_id), max(0, amount))

    def _fmt(self, amount: int) -> str:
        return f"{self.currency_emoji} **{amount:,} {self.currency_name}**"

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def on_load(self) -> None:
        plugin = self

        @self.bot.command("balance", description="Check your coin balance", aliases=["bal"])
        async def balance_cmd(ctx) -> None:
            if not ctx.server_id:
                return await ctx.reply("❌ Economy only works in a server.")
            target = ctx.mentions[0] if ctx.mentions else ctx.author
            bal = await plugin._get_balance(ctx.server_id, target.id)
            await ctx.reply(f"💰 **{target.username}** has {plugin._fmt(bal)}.")

        @self.bot.command("daily", description="Claim your daily coin reward")
        async def daily_cmd(ctx) -> None:
            if not ctx.server_id:
                return await ctx.reply("❌ Economy only works in a server.")
            uid = ctx.author.id
            daily_key = plugin._daily_key(ctx.server_id, uid)
            last_claim = await plugin.bot.store.get(daily_key)
            now = time.time()
            if last_claim and now - float(last_claim) < 86400:
                remaining = 86400 - (now - float(last_claim))
                h, m = divmod(int(remaining), 3600)
                m //= 60
                return await ctx.reply(f"⏳ You already claimed your daily reward. Come back in **{h}h {m}m**.")
            bal = await plugin._get_balance(ctx.server_id, uid)
            bal += plugin.daily_amount
            await plugin._set_balance(ctx.server_id, uid, bal)
            await plugin.bot.store.set(daily_key, now)
            await ctx.reply(
                f"✅ You claimed your daily {plugin._fmt(plugin.daily_amount)}! "
                f"New balance: {plugin._fmt(bal)}."
            )

        @self.bot.command("give", description="Give coins to another user")
        async def give_cmd(ctx) -> None:
            if not ctx.server_id:
                return await ctx.reply("❌ Economy only works in a server.")
            if not ctx.mentions or len(ctx.args) < 2:
                return await ctx.reply("Usage: `/give @user <amount>`")
            target = ctx.mentions[0]
            if target.id == ctx.author.id:
                return await ctx.reply("❌ You can't give coins to yourself.")
            try:
                amount = int(ctx.args[-1])
                if amount <= 0:
                    raise ValueError
            except ValueError:
                return await ctx.reply("❌ Amount must be a positive integer.")
            sender_bal = await plugin._get_balance(ctx.server_id, ctx.author.id)
            if sender_bal < amount:
                return await ctx.reply(f"❌ You only have {plugin._fmt(sender_bal)}.")
            await plugin._set_balance(ctx.server_id, ctx.author.id, sender_bal - amount)
            target_bal = await plugin._get_balance(ctx.server_id, target.id)
            await plugin._set_balance(ctx.server_id, target.id, target_bal + amount)
            await ctx.reply(
                f"✅ {mention(ctx.author.id)} gave {plugin._fmt(amount)} to {mention(target.id)}!"
            )

        @self.bot.command("richest", description="Top-10 richest users in the server")
        async def richest_cmd(ctx) -> None:
            if not ctx.server_id:
                return await ctx.reply("❌ Economy only works in a server.")
            keys = await plugin.bot.store.keys(f"eco:{ctx.server_id}:*")
            # Exclude daily-claim keys
            keys = [k for k in keys if not k.startswith(f"eco:daily:")]
            if not keys:
                return await ctx.reply("No economy data yet!")
            entries = []
            for key in keys:
                uid = key.rsplit(":", 1)[-1]
                bal = int((await plugin.bot.store.get(key)) or 0)
                entries.append((uid, bal))
            entries.sort(key=lambda x: -x[1])
            medals = ["🥇", "🥈", "🥉"]
            lines = [f"💰 **Top {min(10, len(entries))} Richest**"]
            for i, (uid, bal) in enumerate(entries[:10]):
                user = plugin.bot.cache.users.get(uid)
                name = user.username if user else uid
                medal = medals[i] if i < 3 else f"#{i+1}"
                lines.append(f"{medal} **{name}** — {plugin._fmt(bal)}")
            await ctx.reply("\n".join(lines))
