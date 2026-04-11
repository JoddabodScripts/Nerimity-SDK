"""Middleware pipeline for prefix commands.

Middleware functions wrap command execution, enabling cross-cutting concerns
like logging, permission checks, and metrics without touching command handlers.

A middleware has the signature::

    async def my_middleware(ctx: Context, call_next: Callable) -> None:
        # before
        await call_next(ctx)
        # after

Usage::

    from nerimity_sdk.commands.middleware import (
        MiddlewarePipeline,
        log_middleware,
        guild_only_middleware,
        require_permission_middleware,
    )

    pipeline = MiddlewarePipeline()
    pipeline.use(log_middleware)
    pipeline.use(guild_only_middleware)

    # Attach to a CommandRouter:
    router.global_middleware.append(pipeline.build())

    # Or apply to a single command:
    @bot.command("ban")
    @pipeline.apply
    async def ban(ctx): ...
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Coroutine, TYPE_CHECKING

if TYPE_CHECKING:
    from nerimity_sdk.context.ctx import Context

Middleware = Callable[["Context", Callable], Coroutine[Any, Any, None]]

logger = logging.getLogger("nerimity.middleware")


class MiddlewarePipeline:
    """Ordered chain of middleware functions.

    Call :meth:`use` to append middleware, then :meth:`build` to get a single
    composed middleware you can attach to a router or command.
    """

    def __init__(self) -> None:
        self._stack: list[Middleware] = []

    def use(self, middleware: Middleware) -> "MiddlewarePipeline":
        """Append *middleware* to the pipeline.  Returns *self* for chaining."""
        self._stack.append(middleware)
        return self

    def build(self) -> Middleware:
        """Return a single middleware that runs the whole stack in order."""
        stack = list(self._stack)

        async def composed(ctx: "Context", call_next: Callable) -> None:
            async def run(index: int) -> None:
                if index >= len(stack):
                    await call_next(ctx)
                    return
                await stack[index](ctx, lambda _ctx: run(index + 1))

            await run(0)

        return composed

    def apply(self, handler: Callable) -> Callable:
        """Decorator — wrap a command handler with this pipeline."""
        composed = self.build()

        async def wrapped(ctx: "Context") -> None:
            await composed(ctx, handler)

        wrapped.__name__ = getattr(handler, "__name__", "wrapped")
        return wrapped


# ── Built-in middleware ───────────────────────────────────────────────────────

async def log_middleware(ctx: "Context", call_next: Callable) -> None:
    """Log command name, author, and execution time."""
    start = time.perf_counter()
    logger.info("cmd=%s user=%s server=%s", ctx.command_name, ctx.author.id, ctx.server_id)
    try:
        await call_next(ctx)
    finally:
        elapsed = (time.perf_counter() - start) * 1000
        logger.debug("cmd=%s done in %.1fms", ctx.command_name, elapsed)


async def guild_only_middleware(ctx: "Context", call_next: Callable) -> None:
    """Reject commands sent outside a server."""
    if not ctx.server_id:
        await ctx.reply("❌ This command can only be used inside a server.")
        return
    await call_next(ctx)


async def dm_only_middleware(ctx: "Context", call_next: Callable) -> None:
    """Reject commands sent inside a server."""
    if ctx.server_id:
        await ctx.reply("❌ This command can only be used in DMs.")
        return
    await call_next(ctx)


def require_permission_middleware(*perms: str) -> Middleware:
    """Return middleware that checks the author has all *perms* flags.

    Example::

        pipeline.use(require_permission_middleware("kick_members", "ban_members"))
    """
    async def _check(ctx: "Context", call_next: Callable) -> None:
        from nerimity_sdk.permissions.checker import has_permission
        member = ctx.member
        if member is None:
            await ctx.reply("❌ Could not resolve your permissions.")
            return
        for perm in perms:
            if not has_permission(member.permissions, perm):
                await ctx.reply(f"❌ You need the `{perm}` permission.")
                return
        await call_next(ctx)

    return _check
