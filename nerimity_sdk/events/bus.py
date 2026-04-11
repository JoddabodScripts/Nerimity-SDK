"""Event bus with wildcard topic subscriptions.

Provides a pub/sub layer on top of the existing ``EventEmitter``.  Topics are
dot-separated strings (e.g. ``"message.created"``) and support ``*`` (single
segment) and ``**`` (any number of segments) wildcards.

Usage::

    from nerimity_sdk.events.bus import EventBus

    bus = EventBus()

    # Exact subscription
    @bus.subscribe("message.created")
    async def on_msg(event):
        print(event)

    # Wildcard — all message events
    @bus.subscribe("message.*")
    async def on_any_message(event):
        print(event)

    # Deep wildcard — everything
    @bus.subscribe("**")
    async def on_everything(event):
        print(event)

    # Publish
    await bus.publish("message.created", payload)

    # One-shot subscription
    await bus.wait_for("member.joined", timeout=30)
"""
from __future__ import annotations

import asyncio
import fnmatch
import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger("nerimity.bus")

Handler = Callable[[Any], Coroutine[Any, Any, None]]


def _matches(pattern: str, topic: str) -> bool:
    """Return True if *topic* matches *pattern*.

    ``*``  matches exactly one segment.
    ``**`` matches any number of segments (including zero).
    """
    if pattern == "**":
        return True
    # Convert bus pattern to fnmatch glob
    glob = pattern.replace("**", "\x00").replace("*", "[^.]*").replace("\x00", "*")
    return fnmatch.fnmatchcase(topic, glob)


class EventBus:
    """Async pub/sub event bus with wildcard topic matching.

    Parameters
    ----------
    propagate_errors:
        If ``True`` (default ``False``), exceptions raised by handlers are
        re-raised after all handlers have been called.
    """

    def __init__(self, propagate_errors: bool = False) -> None:
        self.propagate_errors = propagate_errors
        # pattern → list of handlers
        self._subs: dict[str, list[Handler]] = {}
        # one-shot futures: pattern → list of (future, predicate)
        self._waiters: dict[str, list[tuple[asyncio.Future, Callable | None]]] = {}

    # ── Subscribe ─────────────────────────────────────────────────────────────

    def subscribe(self, pattern: str) -> Callable[[Handler], Handler]:
        """Decorator — register a handler for *pattern*."""
        def decorator(fn: Handler) -> Handler:
            self._subs.setdefault(pattern, []).append(fn)
            return fn
        return decorator

    def unsubscribe(self, pattern: str, handler: Handler) -> None:
        """Remove a specific handler from *pattern*."""
        handlers = self._subs.get(pattern, [])
        try:
            handlers.remove(handler)
        except ValueError:
            pass

    # ── Publish ───────────────────────────────────────────────────────────────

    async def publish(self, topic: str, payload: Any = None) -> None:
        """Dispatch *payload* to all handlers whose pattern matches *topic*."""
        errors: list[Exception] = []

        for pattern, handlers in list(self._subs.items()):
            if _matches(pattern, topic):
                for handler in list(handlers):
                    try:
                        await handler(payload)
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("bus handler error (topic=%s pattern=%s)", topic, pattern)
                        errors.append(exc)

        # Resolve one-shot waiters
        for pattern, waiters in list(self._waiters.items()):
            if _matches(pattern, topic):
                remaining = []
                for fut, predicate in waiters:
                    if fut.done():
                        continue
                    if predicate is None or predicate(payload):
                        fut.set_result(payload)
                    else:
                        remaining.append((fut, predicate))
                self._waiters[pattern] = remaining

        if self.propagate_errors and errors:
            raise errors[0]

    # ── One-shot wait ─────────────────────────────────────────────────────────

    async def wait_for(
        self,
        pattern: str,
        timeout: float | None = None,
        predicate: Callable[[Any], bool] | None = None,
    ) -> Any:
        """Wait for the next event matching *pattern* and return its payload.

        Parameters
        ----------
        timeout:
            Seconds to wait before raising ``asyncio.TimeoutError``.
        predicate:
            Optional callable; only resolves when ``predicate(payload)`` is truthy.
        """
        loop = asyncio.get_event_loop()
        fut: asyncio.Future = loop.create_future()
        self._waiters.setdefault(pattern, []).append((fut, predicate))
        try:
            return await asyncio.wait_for(asyncio.shield(fut), timeout=timeout)
        except asyncio.TimeoutError:
            # Clean up the dangling future
            waiters = self._waiters.get(pattern, [])
            self._waiters[pattern] = [(f, p) for f, p in waiters if f is not fut]
            raise

    # ── Introspection ─────────────────────────────────────────────────────────

    def patterns(self) -> list[str]:
        """Return all registered patterns."""
        return list(self._subs.keys())

    def listener_count(self, pattern: str) -> int:
        """Return the number of handlers registered for *pattern*."""
        return len(self._subs.get(pattern, []))
