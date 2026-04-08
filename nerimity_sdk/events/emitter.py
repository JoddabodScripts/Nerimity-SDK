"""Typed async event emitter with wildcard and once() support."""
from __future__ import annotations
import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine

Handler = Callable[..., Coroutine[Any, Any, None]]


class EventEmitter:
    def __init__(self) -> None:
        self._listeners: dict[str, list[tuple[Handler, bool]]] = defaultdict(list)

    def on(self, event: str, handler: Handler) -> None:
        self._listeners[event].append((handler, False))

    def once(self, event: str, handler: Handler) -> None:
        self._listeners[event].append((handler, True))

    def off(self, event: str, handler: Handler) -> None:
        self._listeners[event] = [
            (h, o) for h, o in self._listeners[event] if h is not handler
        ]

    async def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        handlers = self._listeners.get(event, []) + self._listeners.get("*", [])
        keep: list[tuple[Handler, bool]] = []
        tasks = []
        for handler, once in handlers:
            tasks.append(_safe_call(handler, *args, **kwargs))
            if not once:
                keep.append((handler, once))
        # Rebuild non-wildcard listeners (remove consumed once handlers)
        if event != "*":
            self._listeners[event] = [
                (h, o) for h, o in self._listeners[event] if not o
            ]
        if tasks:
            await asyncio.gather(*tasks)


async def _safe_call(handler: Handler, *args: Any, **kwargs: Any) -> None:
    from nerimity_sdk.utils.logging import get_logger
    try:
        await handler(*args, **kwargs)
    except Exception as exc:
        get_logger().error(f"Unhandled error in event handler {handler.__name__!r}: {exc}")
