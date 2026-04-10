"""TranslatePlugin — auto-translate messages in a channel using MyMemory (free, no key).

Usage::

    await bot.plugins.load(TranslatePlugin(
        watch_channel_id="123",
        target_lang="en",
    ))

Or as a command::

    @bot.command("translate")
    async def translate(ctx):
        text = " ".join(ctx.args)
        result = await ctx.bot_plugins["translate"].translate(text, "en")
        await ctx.reply(result)
"""
from __future__ import annotations
from nerimity_sdk.plugins.manager import PluginBase, listener


class TranslatePlugin(PluginBase):
    name = "translate"

    def __init__(self, watch_channel_id: str | None = None,
                 target_lang: str = "en") -> None:
        super().__init__()
        self.watch_channel_id = watch_channel_id
        self.target_lang = target_lang

    async def translate(self, text: str, target: str = "en") -> str:
        """Translate text using MyMemory (free, no API key required)."""
        import urllib.parse
        import aiohttp
        url = (
            f"https://api.mymemory.translated.net/get"
            f"?q={urllib.parse.quote(text)}&langpair=autodetect|{target}"
        )
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                data = await resp.json()
        return data.get("responseData", {}).get("translatedText", text)

    @listener("message:created")
    async def on_message(self, event) -> None:
        from nerimity_sdk.events.payloads import MessageCreatedEvent
        if not isinstance(event, MessageCreatedEvent):
            return
        msg = event.message
        if msg.channel_id != self.watch_channel_id:
            return
        if self.bot._me and msg.created_by.id == self.bot._me.id:
            return
        translated = await self.translate(msg.content or "", self.target_lang)
        if translated.lower() != (msg.content or "").lower():
            await self.bot.rest.create_message(
                msg.channel_id, f"🌐 *{translated}*"
            )
