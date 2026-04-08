"""nerimity-help — quick reference for the nerimity-sdk."""


HELP = """
nerimity-sdk — Quick Reference
================================

INSTALL
  pip install nerimity-sdk
  pip install "nerimity-sdk[cron,watch,sqlite,redis]"

SCAFFOLD A PROJECT
  nerimity create my-bot
  cd my-bot && python bot.py

TOKEN SETUP  (.env file — never hardcode your token)
  NERIMITY_TOKEN=your_token_here

  In bot.py:
    from dotenv import load_dotenv; load_dotenv()
    import os
    bot = Bot(token=os.environ["NERIMITY_TOKEN"])

BOT BASICS
  bot = Bot(token=..., prefix="!")

  @bot.on("ready")
  async def on_ready(me): print(f"Logged in as {me.username}")

  @bot.command("ping")
  async def ping(ctx): await ctx.reply("Pong!")

  bot.run()

COMMANDS
  @bot.command("kick", args=[MemberConverter], guild_only=True, cooldown=5.0)
  async def kick(ctx):
      member = ctx.args[0]                    # already a Member object
      if not await ctx.confirm("Sure?"): return
      await ctx.rest.kick_member(ctx.server_id, member.user.id)

  Converters: Int, MemberConverter, UserConverter, ChannelConverter
  Flags:      !cmd --silent --count=3  →  ctx.flags["silent"], ctx.flags["count"]

SLASH COMMANDS
  @bot.slash("info", description="Bot info")
  async def info(sctx): await sctx.reply("Hello!")

BUTTONS
  @bot.button("confirm:{action}:{target}", ttl=300)
  async def on_confirm(bctx):
      await bctx.reply(f"{bctx.params['action']} on {bctx.params['target']}")

CONTEXT HELPERS
  await ctx.reply(content)
  await ctx.react("👍")
  await ctx.ask("What's your name?", timeout=30)
  await ctx.confirm("Are you sure?")
  ctx.mentions          # list[User] resolved from [@:id] in message
  mention(user_id)      # → "[@:user_id]"

PAGINATOR
  from nerimity_sdk import Paginator
  await Paginator(["Page 1", "Page 2", "Page 3"]).send(ctx)

EVENTS
  @bot.on("message:created")   # MessageCreatedEvent — fully typed
  @bot.on("server:member_joined")
  @bot.on("*")                 # wildcard

ERROR HANDLERS
  @bot.on_command_error
  async def on_error(ctx, error): await ctx.reply(f"❌ {error}")

PLUGINS
  class MyPlugin(PluginBase):
      name = "my_plugin"
      @listener("message:created")
      async def on_msg(self, event): ...

  await bot.plugins.load(MyPlugin())
  await bot.plugins.reload("my_plugin")   # hot reload

STORAGE
  bot = Bot(token=..., store=JsonStore("data.json"))
  await bot.store.set("guild:123:prefix", "?")
  await bot.store.get("guild:123:prefix")

SCHEDULER
  @bot.cron("0 9 * * 1")   # every Monday 09:00 UTC (pip install croniter)
  async def weekly(): await bot.rest.create_message(CHANNEL, "Morning!")

PERMISSIONS
  from nerimity_sdk import has_permission, Permissions
  has_permission(member, server, Permissions.KICK_MEMBERS)

CLI COMMANDS
  nerimity create <name>   scaffold a new bot project
  nerimity version         show SDK version
  nerimity-help            this help text

DOCS
  https://nerimity-sdk.readthedocs.io
"""


def main():
    print(HELP)
