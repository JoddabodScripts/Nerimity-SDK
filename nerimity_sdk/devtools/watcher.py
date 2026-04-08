"""Dev watch mode: auto-reload plugins when their .py file changes on disk.

Requires watchfiles: pip install watchfiles

Usage::

    bot = Bot(token="...", watch=True)
    # or manually:
    from nerimity_sdk.devtools.watcher import Watcher
    watcher = Watcher(bot)
    await watcher.start()
"""
from __future__ import annotations
import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from nerimity_sdk.bot import Bot


class Watcher:
    def __init__(self, bot: "Bot", paths: Optional[list[str]] = None) -> None:
        self._bot = bot
        self._paths = paths or ["plugins"]
        self._task: Optional[asyncio.Task] = None

    async def _watch(self) -> None:
        try:
            from watchfiles import awatch
        except ImportError:
            raise ImportError("Install watchfiles: pip install watchfiles")

        self._bot.logger.info(f"[Watcher] Watching: {self._paths}")
        async for changes in awatch(*self._paths):
            for _, path in changes:
                await self._handle_change(path)

    async def _handle_change(self, path: str) -> None:
        p = Path(path)
        if p.suffix != ".py":
            return
        # Find which loaded plugin came from this file
        for name, plugin in list(self._bot.plugins._plugins.items()):
            mod = type(plugin).__module__
            import sys
            mod_obj = sys.modules.get(mod)
            if mod_obj and getattr(mod_obj, "__file__", None) == str(p.resolve()):
                self._bot.logger.info(f"[Watcher] Reloading plugin: {name} ({p.name})")
                try:
                    await self._bot.plugins.reload(name)
                except Exception as exc:
                    self._bot.logger.error(f"[Watcher] Reload failed for {name}: {exc}")
                return
        # If not a known plugin, try load_from_path
        self._bot.logger.info(f"[Watcher] New file detected: {p.name} — use bot.plugins.load_from_path() to load it")

    async def start(self) -> None:
        self._task = asyncio.create_task(self._watch())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
