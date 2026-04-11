"""TagPlugin — custom server tags / text snippets.

Lets moderators define short named snippets that anyone can retrieve with
``/tag <name>``.

Commands
--------
``/tag <name>``          — post the tag's content.
``/tag add <name> <content>``  — create or overwrite a tag (mod only).
``/tag delete <name>``   — delete a tag (mod only).
``/tag list``            — list all tag names in this server.

Tags are stored in the bot's store under ``tag:<server_id>:<name>``.

Usage::

    await bot.plugins.load(TagPlugin(
        mod_role_ids=["111222333"],   # roles allowed to add/delete tags
    ))
"""
from __future__ import annotations

from nerimity_sdk.plugins.manager import PluginBase


class TagPlugin(PluginBase):
    """Custom server text snippets."""
    name = "tags"

    def __init__(self, mod_role_ids: list[str] | None = None) -> None:
        super().__init__()
        self.mod_role_ids: set[str] = set(mod_role_ids or [])

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _key(self, server_id: str, name: str) -> str:
        return f"tag:{server_id}:{name.lower()}"

    def _index_key(self, server_id: str) -> str:
        return f"tag:index:{server_id}"

    def _is_mod(self, ctx) -> bool:
        if not self.mod_role_ids:
            return True  # no restriction configured
        member = ctx.member
        if member is None:
            return False
        return bool(self.mod_role_ids.intersection(getattr(member, "role_ids", [])))

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def on_load(self) -> None:
        plugin = self

        @self.bot.command("tag", description="Retrieve or manage server tags")
        async def tag_cmd(ctx) -> None:
            if not ctx.server_id:
                return await ctx.reply("❌ Tags only work inside a server.")

            args = ctx.args
            if not args:
                return await ctx.reply("Usage: `/tag <name>` | `/tag add <name> <content>` | `/tag delete <name>` | `/tag list`")

            sub = args[0].lower()

            # ── /tag list ────────────────────────────────────────────────────
            if sub == "list":
                raw = await plugin.bot.store.get(plugin._index_key(ctx.server_id))
                names: list[str] = raw if isinstance(raw, list) else []
                if not names:
                    return await ctx.reply("No tags defined yet.")
                return await ctx.reply("📋 **Tags:** " + ", ".join(f"`{n}`" for n in sorted(names)))

            # ── /tag add <name> <content> ────────────────────────────────────
            if sub == "add":
                if not plugin._is_mod(ctx):
                    return await ctx.reply("❌ You don't have permission to add tags.")
                if len(args) < 3:
                    return await ctx.reply("Usage: `/tag add <name> <content>`")
                name = args[1].lower()
                content = " ".join(args[2:])
                await plugin.bot.store.set(plugin._key(ctx.server_id, name), content)
                # Update index
                raw = await plugin.bot.store.get(plugin._index_key(ctx.server_id))
                names = raw if isinstance(raw, list) else []
                if name not in names:
                    names.append(name)
                    await plugin.bot.store.set(plugin._index_key(ctx.server_id), names)
                return await ctx.reply(f"✅ Tag `{name}` saved.")

            # ── /tag delete <name> ───────────────────────────────────────────
            if sub == "delete":
                if not plugin._is_mod(ctx):
                    return await ctx.reply("❌ You don't have permission to delete tags.")
                if len(args) < 2:
                    return await ctx.reply("Usage: `/tag delete <name>`")
                name = args[1].lower()
                await plugin.bot.store.delete(plugin._key(ctx.server_id, name))
                raw = await plugin.bot.store.get(plugin._index_key(ctx.server_id))
                names = raw if isinstance(raw, list) else []
                if name in names:
                    names.remove(name)
                    await plugin.bot.store.set(plugin._index_key(ctx.server_id), names)
                return await ctx.reply(f"🗑️ Tag `{name}` deleted.")

            # ── /tag <name> ──────────────────────────────────────────────────
            name = sub
            content = await plugin.bot.store.get(plugin._key(ctx.server_id, name))
            if content is None:
                return await ctx.reply(f"❓ No tag named `{name}`. Use `/tag list` to see all tags.")
            await ctx.reply(str(content))
