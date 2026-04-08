"""
Example bot — demonstrates every major nerimity-sdk feature:
  - Prefix commands with arg converters, cooldowns, middleware
  - ctx.confirm(), ctx.ask(), ctx.mentions
  - Slash commands
  - Buttons + ButtonContext
  - Paginator
  - Scheduled tasks (@bot.cron)
  - Persistent storage (JsonStore)
  - Global error handlers
  - Plugin system

Run:
    pip install "nerimity-sdk[cron]"
    cp .env.example .env   # add your token
    python example_bot/bot.py
"""
import asyncio
import os
from dotenv import load_dotenv
from nerimity_sdk import (
    Bot, Paginator, Embed, MessageBuilder,
    Button, ComponentRow,
    mention, JsonStore,
    Int, MemberConverter,
)

load_dotenv()
TOKEN = os.environ["NERIMITY_TOKEN"]
ANNOUNCE_CHANNEL = os.environ.get("ANNOUNCE_CHANNEL", "")

bot = Bot(
    token=TOKEN,
    prefix="!",
    store=JsonStore("bot_data.json"),
    debug=False,
)


# ── Error handlers ────────────────────────────────────────────────────────────

@bot.on_command_error
async def on_command_error(ctx, error):
    await ctx.reply(f"❌ {error}")


@bot.on_slash_error
async def on_slash_error(sctx, error):
    await sctx.reply(f"❌ Slash error: {error}")


@bot.on_button_error
async def on_button_error(bctx, error):
    await bctx.reply(f"❌ Button error: {error}")


# ── Ready ─────────────────────────────────────────────────────────────────────

@bot.on("ready")
async def on_ready(me):
    print(f"✅ Logged in as {me.username}#{me.tag}")


# ── Prefix commands ───────────────────────────────────────────────────────────

@bot.command("ping", description="Latency check", category="Utility")
async def ping(ctx):
    await ctx.reply("Pong! 🏓")


@bot.command(
    "add",
    description="Add two numbers",
    usage="<a> <b>",
    args=[Int, Int],
    category="Utility",
)
async def add(ctx):
    # ctx.args are already ints thanks to converters
    a, b = ctx.args
    await ctx.reply(f"{a} + {b} = {a + b}")


@bot.command(
    "kick",
    description="Kick a member",
    usage="<@member> [reason]",
    guild_only=True,
    args=[MemberConverter],
    category="Moderation",
)
async def kick(ctx):
    member = ctx.args[0]
    reason = " ".join(ctx.args[1:]) if len(ctx.args) > 1 else "No reason given"

    confirmed = await ctx.confirm(
        f"Kick {mention(member.user.id)} for: {reason}?"
    )
    if not confirmed:
        return await ctx.reply("Cancelled.")

    await ctx.rest.kick_member(ctx.server_id, member.user.id)
    await ctx.reply(f"👢 Kicked {mention(member.user.id)}: {reason}")


@bot.command("help", description="Show commands", category="Utility")
async def help_cmd(ctx):
    pages = bot.router.help_text().split("\n\n")  # one page per category
    await Paginator(pages or ["No commands found."]).send(ctx)


@bot.command("setprefix", description="Set a custom prefix for this server",
             guild_only=True, usage="<prefix>")
async def setprefix(ctx):
    if not ctx.args:
        return await ctx.reply("Usage: !setprefix <prefix>")
    new_prefix = ctx.args[0]
    await bot.prefix_resolver.set(ctx.server_id, new_prefix)
    await bot.store.set(f"guild:{ctx.server_id}:prefix", new_prefix)
    await ctx.reply(f"✅ Prefix set to `{new_prefix}`")


@bot.command("mentions", description="List mentioned users")
async def show_mentions(ctx):
    users = ctx.mentions
    if not users:
        return await ctx.reply("No mentions found.")
    names = ", ".join(f"{u.username}#{u.tag}" for u in users)
    await ctx.reply(f"Mentioned: {names}")


@bot.command("clear", description="Delete N messages (1–100)",
             guild_only=True, usage="<count>", args=[Int])
async def clear(ctx):
    count: int = ctx.args[0]
    if not 1 <= count <= 100:
        return await ctx.reply("Count must be between 1 and 100.")

    confirmed = await ctx.confirm(f"Delete {count} messages?")
    if not confirmed:
        return await ctx.reply("Cancelled.")

    msgs = await ctx.fetch_messages(limit=count)
    for msg in msgs:
        await ctx.rest.delete_message(ctx.channel_id, msg.id)
    await ctx.reply(f"🗑️ Deleted {len(msgs)} messages.")


# ── Slash commands ────────────────────────────────────────────────────────────

@bot.slash("info", description="Show bot info")
async def slash_info(sctx):
    from nerimity_sdk import __version__
    await sctx.reply(f"nerimity-sdk v{__version__} — running as {bot._me.username if bot._me else '?'}")


@bot.slash("ban", description="Ban a user", args_hint="<user_id> [reason]")
async def slash_ban(sctx):
    parts = sctx.args.split(None, 1)
    if not parts:
        return await sctx.reply("Usage: /ban <user_id> [reason]")
    user_id = parts[0]
    reason = parts[1] if len(parts) > 1 else "No reason"
    await sctx.rest.ban_member(sctx.server_id, user_id)
    await sctx.reply(f"🔨 Banned {mention(user_id)}: {reason}")


# ── Buttons ───────────────────────────────────────────────────────────────────

@bot.command("poll", description="Start a yes/no poll", usage="<question>")
async def poll(ctx):
    question = " ".join(ctx.args) if ctx.args else "Do you agree?"
    msg = await ctx.reply(question)

    row = ComponentRow()
    row.add(Button(id=f"poll:yes:{msg.id}", label="👍 Yes"))
    row.add(Button(id=f"poll:no:{msg.id}", label="👎 No"))

    # Register handlers with 5-minute TTL
    @bot.button(f"poll:yes:{msg.id}", ttl=300)
    async def on_yes(bctx):
        user = bctx.user
        name = f"{user.username}#{user.tag}" if user else bctx.user_id
        await bctx.reply(f"✅ {name} voted **Yes**")

    @bot.button(f"poll:no:{msg.id}", ttl=300)
    async def on_no(bctx):
        user = bctx.user
        name = f"{user.username}#{user.tag}" if user else bctx.user_id
        await bctx.reply(f"❌ {name} voted **No**")


@bot.button("confirm:{action}:{target}")
async def on_confirm_button(bctx):
    action = bctx.params["action"]
    target = bctx.params["target"]
    await bctx.reply(f"Confirmed: {action} on {target}")


# ── Scheduled tasks ───────────────────────────────────────────────────────────

if ANNOUNCE_CHANNEL:
    @bot.cron("0 9 * * 1")  # Every Monday at 09:00 UTC
    async def weekly_announcement():
        await bot.rest.create_message(ANNOUNCE_CHANNEL, "📅 Good morning! Have a great week.")


# ── Plugin example (inline) ───────────────────────────────────────────────────

from nerimity_sdk import PluginBase, listener

class WelcomePlugin(PluginBase):
    name = "welcome"
    description = "Greets new members"

    @listener("server:member_joined")
    async def on_join(self, event):
        from nerimity_sdk.events.payloads import MemberJoinedEvent
        if isinstance(event, MemberJoinedEvent):
            # Try to find a general channel
            server = self.bot.cache.servers.get(event.server_id)
            if server and server.channels:
                channel_id = next(iter(server.channels))
                await self.bot.rest.create_message(
                    channel_id,
                    f"👋 Welcome {mention(event.member.user.id)}!"
                )

    async def on_ready(self):
        print(f"[{self.name}] Plugin ready")


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    await bot.plugins.load(WelcomePlugin())
    bot.run()


if __name__ == "__main__":
    asyncio.run(main())
