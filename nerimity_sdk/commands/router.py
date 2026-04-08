"""Prefix command router with argument parsing, middleware, and help generation."""
from __future__ import annotations
import shlex
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from nerimity_sdk.context.ctx import Context

Handler = Callable[["Context"], Coroutine[Any, Any, None]]
Middleware = Callable[["Context", Callable], Coroutine[Any, Any, None]]


@dataclass
class CommandDef:
    name: str
    handler: Handler
    description: str = ""
    usage: str = ""
    category: str = "General"
    aliases: list[str] = field(default_factory=list)
    guild_only: bool = False
    required_user_perms: list = field(default_factory=list)
    required_bot_perms: list = field(default_factory=list)
    middleware: list[Middleware] = field(default_factory=list)
    cooldown: float = 0.0
    converters: list = field(default_factory=list)  # list of converter instances


def _parse_args(text: str) -> tuple[list[str], dict[str, Any]]:
    """Parse a command argument string into positional args and --flag=value flags."""
    try:
        tokens = shlex.split(text)
    except ValueError:
        tokens = text.split()

    args: list[str] = []
    flags: dict[str, Any] = {}
    for token in tokens:
        if token.startswith("--"):
            if "=" in token:
                k, v = token[2:].split("=", 1)
                flags[k] = v
            else:
                flags[token[2:]] = True
        else:
            args.append(token)
    return args, flags


class CommandRouter:
    def __init__(self, prefix: str = "!") -> None:
        self.prefix = prefix
        self._commands: dict[str, CommandDef] = {}
        self._aliases: dict[str, str] = {}
        self._global_middleware: list[Middleware] = []
        self._cooldowns: dict[str, float] = {}  # "user_id:cmd" -> last_used

    def command(
        self,
        name: str,
        *,
        description: str = "",
        usage: str = "",
        category: str = "General",
        aliases: list[str] | None = None,
        guild_only: bool = False,
        required_user_perms: list | None = None,
        required_bot_perms: list | None = None,
        middleware: list[Middleware] | None = None,
        cooldown: float = 0.0,
        args: list | None = None,
    ):
        """Decorator to register a command."""
        def decorator(fn: Handler) -> Handler:
            cmd = CommandDef(
                name=name,
                handler=fn,
                description=description,
                usage=usage,
                category=category,
                aliases=aliases or [],
                guild_only=guild_only,
                required_user_perms=required_user_perms or [],
                required_bot_perms=required_bot_perms or [],
                middleware=middleware or [],
                cooldown=cooldown,
                converters=args or [],
            )
            self._commands[name] = cmd
            for alias in cmd.aliases:
                self._aliases[alias] = name
            return fn
        return decorator

    def use(self, middleware: Middleware) -> None:
        """Register a global middleware applied to every command."""
        self._global_middleware.append(middleware)

    def get_command(self, name: str) -> Optional[CommandDef]:
        canonical = self._aliases.get(name, name)
        return self._commands.get(canonical)

    async def dispatch(self, ctx: "Context") -> bool:
        """Try to dispatch a message as a command. Returns True if handled."""
        content = ctx.message.content
        if not content.startswith(self.prefix):
            return False

        parts = content[len(self.prefix):].split(None, 1)
        if not parts:
            return False

        cmd_name = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        cmd = self.get_command(cmd_name)
        if not cmd:
            return False

        args, flags = _parse_args(rest)
        ctx.args[:] = args
        ctx.flags.update(flags)

        # Guild-only guard
        if cmd.guild_only and not ctx.server_id:
            await ctx.reply("This command can only be used in a server.")
            return True

        # Cooldown check
        if cmd.cooldown > 0:
            key = f"{ctx.author.id}:{cmd.name}"
            last = self._cooldowns.get(key, 0)
            remaining = cmd.cooldown - (time.monotonic() - last)
            if remaining > 0:
                await ctx.reply(f"Slow down! Try again in {remaining:.1f}s.")
                return True
            self._cooldowns[key] = time.monotonic()

        # Permission checks
        if cmd.required_user_perms and ctx.server_id:
            from nerimity_sdk.permissions.checker import has_permission
            server = ctx.server
            member = ctx.member
            if server and member:
                from nerimity_sdk.models import Permissions
                for perm in cmd.required_user_perms:
                    if not has_permission(member, server, perm):
                        await ctx.reply(f"You need the `{perm}` permission.")
                        return True

        # Argument converters
        if cmd.converters:
            from nerimity_sdk.commands.converters import convert_args, ConversionError
            try:
                ctx.args[:] = await convert_args(ctx, cmd.converters)
            except ConversionError as e:
                await ctx.reply(str(e))
                return True

        # Build middleware chain
        all_mw = self._global_middleware + cmd.middleware

        async def run_handler(c: "Context") -> None:
            await cmd.handler(c)

        chain = run_handler
        for mw in reversed(all_mw):
            prev = chain
            async def make_next(c: "Context", _mw=mw, _prev=prev) -> None:
                await _mw(c, _prev)
            chain = make_next

        await chain(ctx)
        return True

    def help_text(self, category: Optional[str] = None) -> str:
        """Generate help text from command metadata."""
        lines = []
        cats: dict[str, list[CommandDef]] = {}
        for cmd in self._commands.values():
            cats.setdefault(cmd.category, []).append(cmd)

        for cat, cmds in sorted(cats.items()):
            if category and cat.lower() != category.lower():
                continue
            lines.append(f"**{cat}**")
            for cmd in cmds:
                aliases = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
                usage = f" `{cmd.usage}`" if cmd.usage else ""
                lines.append(f"  `{self.prefix}{cmd.name}`{usage}{aliases} — {cmd.description}")
        return "\n".join(lines) or "No commands found."
