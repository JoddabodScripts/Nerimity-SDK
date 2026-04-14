"""Argument converters: auto-parse ctx.args from raw strings into typed values."""
from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nerimity_sdk.context.ctx import Context


class ConversionError(Exception):
    """Raised when an argument fails to convert. Message is user-facing."""


class _Int:
    name = "integer"
    async def convert(self, ctx: "Context", value: str) -> int:
        try:
            return int(value)
        except ValueError:
            raise ConversionError(f"`{value}` is not a valid integer.")


class _Member:
    name = "member"
    async def convert(self, ctx: "Context", value: str) -> Any:
        from nerimity_sdk.utils.mentions import parse_mention_ids
        # Accept [@:id], raw id, or username
        ids = parse_mention_ids(value)
        uid = ids[0] if ids else value.strip()
        if ctx.server_id:
            member = ctx.cache.members.get(f"{ctx.server_id}:{uid}")
            if member:
                return member
        raise ConversionError(f"Could not find member `{value}` in this server.")


class _User:
    name = "user"
    async def convert(self, ctx: "Context", value: str) -> Any:
        from nerimity_sdk.utils.mentions import parse_mention_ids
        ids = parse_mention_ids(value)
        uid = ids[0] if ids else value.strip()
        user = ctx.cache.users.get(uid)
        if user:
            return user
        raise ConversionError(f"Could not find user `{value}`.")


class _Channel:
    name = "channel"
    async def convert(self, ctx: "Context", value: str) -> Any:
        channel = ctx.cache.channels.get(value.strip())
        if channel:
            return channel
        raise ConversionError(f"Could not find channel `{value}`.")


class _Float:
    name = "float"
    async def convert(self, ctx: "Context", value: str) -> float:
        try:
            return float(value)
        except ValueError:
            raise ConversionError(f"`{value}` is not a valid number.")


class _Bool:
    name = "bool"
    _TRUE = {"true", "yes", "1", "on", "y"}
    _FALSE = {"false", "no", "0", "off", "n"}
    async def convert(self, ctx: "Context", value: str) -> bool:
        v = value.lower()
        if v in self._TRUE:
            return True
        if v in self._FALSE:
            return False
        raise ConversionError(f"`{value}` is not a valid yes/no value.")


# Singleton instances used as type annotations in @bot.command(args=[Int, Member])
Int = _Int()
Member = _Member()
User = _User()
Channel = _Channel()
Float = _Float()
Bool = _Bool()


async def convert_args(ctx: "Context", converters: list) -> list:
    """Run converters against ctx.args in order. Returns converted values."""
    results = []
    for i, converter in enumerate(converters):
        if i >= len(ctx.args):
            raise ConversionError(
                f"Missing argument #{i + 1} (expected {converter.name})."
            )
        results.append(await converter.convert(ctx, ctx.args[i]))
    return results


class _Str:
    name = "string"
    async def convert(self, ctx: "Context", value: str) -> str:
        return value


Str = _Str()


def converters_from_annotations(fn) -> list:
    """Extract converters from a command handler's type annotations.

    Supports: int → Int, float → Float, bool → Bool, str → Str (passthrough),
    and the SDK converter singletons.

    Usage::

        @bot.command("add")
        async def add(ctx, a: int, b: int): ...
        # equivalent to args=[Int, Int]
    """
    import inspect
    sig = inspect.signature(fn)
    _type_map = {int: Int, float: Float, bool: Bool, str: Str}
    converters = []
    params = list(sig.parameters.values())
    # Skip the first param (ctx)
    for param in params[1:]:
        ann = param.annotation
        if ann is inspect.Parameter.empty:
            continue
        if ann in _type_map:
            converters.append(_type_map[ann])
        elif hasattr(ann, "convert"):
            converters.append(ann)
    return converters
