"""Cooldown manager for prefix and slash commands.

Provides per-user, per-server, and per-channel cooldown buckets with
automatic expiry.  Integrates with ``CommandRouter`` via the ``cooldown``
parameter on ``@bot.command``, but can also be used standalone.

Usage::

    from nerimity_sdk.commands.cooldowns import CooldownManager, CooldownError

    cm = CooldownManager()

    # Check / consume a cooldown (raises CooldownError if on cooldown)
    await cm.check("ping", user_id="123", rate=1, per=5.0)

    # Standalone decorator
    @cm.cooldown(rate=1, per=10.0, scope="user")
    async def my_handler(ctx): ...

    # Reset a user's cooldown for a command
    cm.reset("ping", user_id="123")
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from nerimity_sdk.context.ctx import Context


class CooldownError(Exception):
    """Raised when a command is invoked while on cooldown.

    Attributes
    ----------
    retry_after:
        Seconds remaining until the cooldown expires.
    """

    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(f"Command on cooldown. Try again in {retry_after:.1f}s.")


@dataclass
class _Bucket:
    """Sliding-window token bucket."""
    rate: int          # max calls per window
    per: float         # window size in seconds
    tokens: int = field(init=False)
    window_start: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = self.rate
        self.window_start = time.monotonic()

    def consume(self) -> float:
        """Try to consume one token.  Returns 0 on success, retry_after on failure."""
        now = time.monotonic()
        if now - self.window_start >= self.per:
            self.tokens = self.rate
            self.window_start = now
        if self.tokens > 0:
            self.tokens -= 1
            return 0.0
        return self.per - (now - self.window_start)


class CooldownManager:
    """Manages per-command cooldown buckets.

    Buckets are keyed by ``(command_name, scope_key)`` where *scope_key* is
    the user ID, server ID, or channel ID depending on the scope.
    """

    def __init__(self) -> None:
        # (command, scope_key) → _Bucket
        self._buckets: dict[tuple[str, str], _Bucket] = {}

    # ── Core API ──────────────────────────────────────────────────────────────

    def check(
        self,
        command: str,
        *,
        scope_key: str,
        rate: int = 1,
        per: float = 5.0,
    ) -> None:
        """Check and consume a cooldown token.

        Raises :class:`CooldownError` if the bucket is exhausted.

        Parameters
        ----------
        command:
            Command name used as part of the bucket key.
        scope_key:
            The user/server/channel ID that identifies the bucket.
        rate:
            Number of allowed calls per *per* seconds.
        per:
            Window size in seconds.
        """
        key = (command, scope_key)
        if key not in self._buckets:
            self._buckets[key] = _Bucket(rate=rate, per=per)
        retry_after = self._buckets[key].consume()
        if retry_after > 0:
            raise CooldownError(retry_after)

    def reset(self, command: str, *, scope_key: str) -> None:
        """Remove the bucket for *(command, scope_key)*, clearing the cooldown."""
        self._buckets.pop((command, scope_key), None)

    def reset_all(self, command: str) -> None:
        """Remove all buckets for *command*."""
        to_delete = [k for k in self._buckets if k[0] == command]
        for k in to_delete:
            del self._buckets[k]

    def remaining(self, command: str, *, scope_key: str) -> float:
        """Return seconds remaining on the cooldown, or 0 if not on cooldown."""
        bucket = self._buckets.get((command, scope_key))
        if bucket is None:
            return 0.0
        now = time.monotonic()
        if now - bucket.window_start >= bucket.per:
            return 0.0
        if bucket.tokens > 0:
            return 0.0
        return bucket.per - (now - bucket.window_start)

    # ── Decorator ─────────────────────────────────────────────────────────────

    def cooldown(
        self,
        rate: int = 1,
        per: float = 5.0,
        scope: str = "user",
    ) -> Callable:
        """Decorator that applies a cooldown to a command handler.

        Parameters
        ----------
        rate:
            Allowed calls per window.
        per:
            Window size in seconds.
        scope:
            ``"user"``, ``"server"``, or ``"channel"``.
        """
        def decorator(fn: Callable) -> Callable:
            async def wrapped(ctx: "Context") -> Any:
                scope_key = _resolve_scope(ctx, scope)
                self.check(fn.__name__, scope_key=scope_key, rate=rate, per=per)
                return await fn(ctx)
            wrapped.__name__ = fn.__name__
            return wrapped
        return decorator


def _resolve_scope(ctx: "Context", scope: str) -> str:
    if scope == "server":
        return ctx.server_id or ctx.author.id
    if scope == "channel":
        return ctx.channel_id
    return ctx.author.id  # default: "user"
