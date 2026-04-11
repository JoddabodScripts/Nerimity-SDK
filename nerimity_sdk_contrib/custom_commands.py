"""CustomCommandPlugin — let admins create simple trigger→response commands at runtime."""
from __future__ import annotations
from nerimity_sdk.plugins.manager import PluginBase, listener


class CustomCommandPlugin(PluginBase):
    """Lets server admins add/remove simple text commands without writing code.

    Usage::

        await bot.plugins.load(CustomCommandPlugin())

    Then in chat:
        /addcmd hello  Hello there!
        /hello          → Hello there!
        /delcmd hello
    """

    name = "custom_commands"
    description = "Runtime custom text commands"

    def __init__(self) -> None:
        super().__init__()
        self._cmds: dict[str, str] = {}  # name → response

    async def on_load(self) -> None:
        # Load persisted commands
        raw = await self.bot.store.get("custom_commands") or {}
        self._cmds = raw

        @self.bot.command("addcmd", description="Add a custom command",
                          usage="<name> <response>", guild_only=True)
        async def addcmd(ctx):
            if len(ctx.args) < 2:
                return await ctx.reply("Usage: /addcmd <name> <response text>")
            name = ctx.args[0].lower()
            response = " ".join(ctx.args[1:])
            self._cmds[name] = response
            await self.bot.store.set("custom_commands", self._cmds)
            await ctx.reply(f"✅ Added command `/{name}`.")

        @self.bot.command("delcmd", description="Remove a custom command",
                          usage="<name>", guild_only=True)
        async def delcmd(ctx):
            if not ctx.args:
                return await ctx.reply("Usage: /delcmd <name>")
            name = ctx.args[0].lower()
            if name not in self._cmds:
                return await ctx.reply(f"❌ No custom command `/{name}` found.")
            del self._cmds[name]
            await self.bot.store.set("custom_commands", self._cmds)
            await ctx.reply(f"🗑 Removed command `/{name}`.")

        @self.bot.command("listcmds", description="List all custom commands")
        async def listcmds(ctx):
            if not self._cmds:
                return await ctx.reply("No custom commands yet. Use /addcmd to add one.")
            lines = [f"`/{k}` → {v}" for k, v in sorted(self._cmds.items())]
            await ctx.reply("\n".join(lines))

    @listener("message:created")
    async def _on_message(self, event) -> None:
        from nerimity_sdk.events.payloads import MessageCreatedEvent
        msg = event.message if isinstance(event, MessageCreatedEvent) else None
        if not msg:
            return
        content = (msg.content or "").strip()
        prefix = self.bot.router.prefix
        if not content.startswith(prefix):
            return
        cmd_name = content[len(prefix):].split()[0].lower() if content[len(prefix):].split() else ""
        if cmd_name in self._cmds:
            await self.bot.rest.create_message(msg.channel_id, self._cmds[cmd_name])
