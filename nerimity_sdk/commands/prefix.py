"""Per-guild prefix config with pluggable storage backend."""
from __future__ import annotations
from typing import Optional, Protocol


class PrefixStore(Protocol):
    async def get(self, guild_id: str) -> Optional[str]: ...
    async def set(self, guild_id: str, prefix: str) -> None: ...
    async def delete(self, guild_id: str) -> None: ...


class MemoryPrefixStore:
    """Default in-memory prefix store."""
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    async def get(self, guild_id: str) -> Optional[str]:
        return self._data.get(guild_id)

    async def set(self, guild_id: str, prefix: str) -> None:
        self._data[guild_id] = prefix

    async def delete(self, guild_id: str) -> None:
        self._data.pop(guild_id, None)


class PrefixResolver:
    """Resolves the command prefix for a given guild, falling back to the global default."""

    def __init__(self, default: str = "!", store: Optional[PrefixStore] = None) -> None:
        self.default = default
        self._store: PrefixStore = store or MemoryPrefixStore()

    async def resolve(self, guild_id: Optional[str]) -> str:
        if guild_id:
            custom = await self._store.get(guild_id)
            if custom:
                return custom
        return self.default

    async def set(self, guild_id: str, prefix: str) -> None:
        await self._store.set(guild_id, prefix)

    async def reset(self, guild_id: str) -> None:
        await self._store.delete(guild_id)
