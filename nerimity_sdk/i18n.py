"""i18n — lightweight localization helper for Nerimity bots.

Supports JSON locale files, per-guild locale overrides, and simple
``{key}`` placeholder substitution.

Usage::

    from nerimity_sdk.i18n import I18n

    i18n = I18n(default_locale="en", locales_dir="locales")
    # locales/en.json → {"ping.reply": "Pong!", "greet": "Hello, {name}!"}
    # locales/ar.json → {"ping.reply": "بونج!", "greet": "مرحباً، {name}!"}

    # In a command:
    locale = await i18n.get_locale(ctx.server_id)
    await ctx.reply(i18n.t("greet", locale, name=ctx.author.username))

    # Override a server's locale:
    await i18n.set_locale(bot.store, ctx.server_id, "ar")
"""
from __future__ import annotations

import json
import os
from typing import Any


class I18n:
    """Locale catalogue with per-guild overrides stored in the bot's store.

    Parameters
    ----------
    default_locale:
        Fallback locale key (e.g. ``"en"``).
    locales_dir:
        Directory that contains ``<locale>.json`` files.  Relative paths are
        resolved from the current working directory at construction time.
    """

    def __init__(self, default_locale: str = "en", locales_dir: str = "locales") -> None:
        self.default_locale = default_locale
        self.locales_dir = os.path.abspath(locales_dir)
        self._cache: dict[str, dict[str, str]] = {}

    # ── Loading ──────────────────────────────────────────────────────────────

    def load(self, locale: str) -> dict[str, str]:
        """Load and cache a locale file.  Returns an empty dict if missing."""
        if locale not in self._cache:
            path = os.path.join(self.locales_dir, f"{locale}.json")
            try:
                with open(path, encoding="utf-8") as fh:
                    self._cache[locale] = json.load(fh)
            except (FileNotFoundError, json.JSONDecodeError):
                self._cache[locale] = {}
        return self._cache[locale]

    def reload(self, locale: str | None = None) -> None:
        """Evict one or all locales from the in-memory cache."""
        if locale:
            self._cache.pop(locale, None)
        else:
            self._cache.clear()

    # ── Translation ──────────────────────────────────────────────────────────

    def t(self, key: str, locale: str | None = None, **kwargs: Any) -> str:
        """Return the translated string for *key*, falling back to the default locale.

        ``{placeholder}`` tokens in the string are replaced with *kwargs*.

        Example::

            i18n.t("greet", "ar", name="Joud")
        """
        locale = locale or self.default_locale
        catalogue = self.load(locale)
        text = catalogue.get(key)
        if text is None and locale != self.default_locale:
            text = self.load(self.default_locale).get(key)
        if text is None:
            text = key  # last resort: return the key itself
        return text.format(**kwargs) if kwargs else text

    # ── Per-guild persistence ─────────────────────────────────────────────────

    @staticmethod
    def _store_key(server_id: str) -> str:
        return f"i18n:locale:{server_id}"

    async def get_locale(self, server_id: str | None, store: Any = None) -> str:
        """Return the active locale for *server_id*, or the default."""
        if server_id and store:
            saved = await store.get(self._store_key(server_id))
            if saved:
                return str(saved)
        return self.default_locale

    async def set_locale(self, store: Any, server_id: str, locale: str) -> None:
        """Persist a locale override for *server_id*."""
        await store.set(self._store_key(server_id), locale)

    # ── Available locales ─────────────────────────────────────────────────────

    def available_locales(self) -> list[str]:
        """Return locale keys discovered from *locales_dir*."""
        try:
            return [
                f[:-5] for f in os.listdir(self.locales_dir) if f.endswith(".json")
            ]
        except FileNotFoundError:
            return []
