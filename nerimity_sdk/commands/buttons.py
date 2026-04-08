"""Button support: builders, ButtonContext, and ButtonRouter with pattern matching + TTL."""
from __future__ import annotations
import asyncio
import fnmatch
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from nerimity_sdk.transport.rest import RESTClient
    from nerimity_sdk.cache.store import Cache

Handler = Callable[["ButtonContext"], Coroutine[Any, Any, None]]


# ── Builders ──────────────────────────────────────────────────────────────────

@dataclass
class Button:
    id: str
    label: str
    alert: bool = False

    def to_dict(self) -> dict:
        d: dict = {"id": self.id, "label": self.label}
        if self.alert:
            d["alert"] = True
        return d


@dataclass
class ComponentRow:
    buttons: list[Button] = field(default_factory=list)

    def add(self, button: Button) -> "ComponentRow":
        self.buttons.append(button)
        return self

    def to_list(self) -> list[dict]:
        return [b.to_dict() for b in self.buttons]


# ── ButtonContext ─────────────────────────────────────────────────────────────

class ButtonContext:
    def __init__(self, payload: dict, rest: "RESTClient", cache: "Cache") -> None:
        self._payload = payload
        self.rest = rest
        self.cache = cache
        self.button_id: str = payload.get("buttonId", "")
        self.message_id: str = payload.get("messageId", "")
        self.channel_id: str = payload.get("channelId", "")
        self.server_id: Optional[str] = payload.get("serverId")
        self.user_id: str = payload.get("userId", "")
        # Parsed wildcard captures from the matched pattern
        self.params: dict[str, str] = {}

    @property
    def user(self):
        return self.cache.users.get(self.user_id)

    async def reply(self, content: str) -> None:
        await self.rest.create_message(self.channel_id, content)

    async def defer(self) -> None:
        """Acknowledge the button click without sending a visible response."""
        # Nerimity button clicks are fire-and-forget from the server side;
        # this is a no-op placeholder for API parity with Discord-style bots.

    async def update_message(self, content: str,
                              buttons: Optional[list[ComponentRow]] = None) -> None:
        """Edit the message that contains the button."""
        body: dict = {"content": content}
        if buttons is not None:
            body["buttons"] = [b for row in buttons for b in row.to_list()]
        await self.rest.update_message(self.channel_id, self.message_id, content)


# ── ButtonRouter ──────────────────────────────────────────────────────────────

@dataclass
class _ButtonRegistration:
    pattern: str
    handler: Handler
    expires_at: Optional[float]  # monotonic time, None = never


class ButtonRouter:
    """Routes message:button_clicked_callback events to handlers by button ID pattern.

    Patterns support fnmatch wildcards:
        @bot.button("confirm:*")          # matches confirm:delete, confirm:ban, …
        @bot.button("page:next:*")        # matches page:next:0, page:next:1, …
    """

    def __init__(self) -> None:
        self._routes: list[_ButtonRegistration] = []

    def register(self, pattern: str, handler: Handler, ttl: Optional[float] = None) -> None:
        expires_at = time.monotonic() + ttl if ttl else None
        self._routes.append(_ButtonRegistration(pattern, handler, expires_at))

    def button(self, pattern: str, ttl: Optional[float] = None):
        """Decorator: @router.button("confirm:{action}:{target}")"""
        def decorator(fn: Handler) -> Handler:
            self.register(pattern, fn, ttl)
            return fn
        return decorator

    def _parse_params(self, pattern: str, button_id: str) -> Optional[dict[str, str]]:
        """Extract named segments from pattern like 'confirm:{action}:{id}'."""
        import re
        # Convert {name} → named capture group
        regex = re.sub(r"\{(\w+)\}", r"(?P<\1>[^:]+)", re.escape(pattern).replace(r"\{", "{").replace(r"\}", "}"))
        # re.escape already escaped braces, redo
        regex = re.sub(r"\\{(\w+)\\}", r"(?P<\1>[^:]+)", re.escape(pattern))
        m = re.fullmatch(regex, button_id)
        return m.groupdict() if m else None

    async def dispatch(self, bctx: "ButtonContext") -> bool:
        now = time.monotonic()
        # Prune expired registrations
        self._routes = [r for r in self._routes if r.expires_at is None or r.expires_at > now]

        for reg in self._routes:
            params = self._parse_params(reg.pattern, bctx.button_id)
            if params is not None:
                bctx.params = params
                await _safe_button_call(reg.handler, bctx)
                return True
            # Fallback: fnmatch
            if fnmatch.fnmatch(bctx.button_id, reg.pattern):
                await _safe_button_call(reg.handler, bctx)
                return True
        return False


async def _safe_button_call(handler: Handler, bctx: "ButtonContext") -> None:
    from nerimity_sdk.utils.logging import get_logger
    try:
        await handler(bctx)
    except Exception as exc:
        get_logger().error(f"[Button] Unhandled error in {handler.__name__!r}: {exc}")
        raise  # re-raise so on_button_error can catch it
