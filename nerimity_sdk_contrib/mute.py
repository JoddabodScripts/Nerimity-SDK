"""MutePlugin — mute/unmute users via a muted role."""
from __future__ import annotations
from nerimity_sdk.plugins.manager import PluginBase, listener


class MutePlugin(PluginBase):
    """Adds /mute and /unmute commands.

    Requires a 'Muted' role to exist on the server (or pass muted_role_id).

    Usage::

        await bot.plugins.load(MutePlugin(log_channel_id="YOUR_LOG_CHANNEL"))
    """

    name = "mute"
    description = "Mute/unmute users"

    def __init__(self, muted_role_id: str = "", log_channel_id: str = "") -> None:
        super().__init__()
        self._muted_role_id = muted_role_id
        self._log_channel_id = log_channel_id

    async def on_load(self) -> None:
        @self.bot.command("mute", description="Mute a user", usage="<user_id> [reason]",
                          guild_only=True)
        async def mute(ctx):
            if not ctx.args:
                return await ctx.reply("Usage: /mute <user_id> [reason]")
            user_id = ctx.args[0]
            reason = " ".join(ctx.args[1:]) or "No reason given"
            role_id = self._muted_role_id
            if not role_id:
                # Try to find a role named "Muted"
                server = ctx.server
                if server:
                    for r in server.roles.values():
                        if r.name.lower() == "muted":
                            role_id = r.id
                            break
            if not role_id:
                return await ctx.reply("❌ No muted role found. Create a role named 'Muted' or pass muted_role_id.")
            try:
                await ctx.rest.add_roles(ctx.server_id, user_id, [role_id])
                await ctx.reply(f"🔇 Muted <@{user_id}>. Reason: {reason}")
                if self._log_channel_id:
                    await ctx.rest.create_message(
                        self._log_channel_id,
                        f"🔇 **Muted** <@{user_id}> by <@{ctx.author.id}>. Reason: {reason}"
                    )
            except Exception as e:
                await ctx.reply(f"❌ Failed to mute: {e}")

        @self.bot.command("unmute", description="Unmute a user", usage="<user_id>",
                          guild_only=True)
        async def unmute(ctx):
            if not ctx.args:
                return await ctx.reply("Usage: /unmute <user_id>")
            user_id = ctx.args[0]
            role_id = self._muted_role_id
            if not role_id:
                server = ctx.server
                if server:
                    for r in server.roles.values():
                        if r.name.lower() == "muted":
                            role_id = r.id
                            break
            if not role_id:
                return await ctx.reply("❌ No muted role found.")
            try:
                await ctx.rest.remove_role(ctx.server_id, user_id, role_id)
                await ctx.reply(f"🔊 Unmuted <@{user_id}>.")
                if self._log_channel_id:
                    await ctx.rest.create_message(
                        self._log_channel_id,
                        f"🔊 **Unmuted** <@{user_id}> by <@{ctx.author.id}>."
                    )
            except Exception as e:
                await ctx.reply(f"❌ Failed to unmute: {e}")
