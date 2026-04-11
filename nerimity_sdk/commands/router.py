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
    converters: list = field(default_factory=list)
    public: bool = True  # if True, registered with Nerimity API as a slash command
    requires: list = field(default_factory=list)  # shortcut permission flags
    cooldown_scope: str = "user"  # "user", "server", or "channel"
    error_handler: Optional[Callable] = None  # per-command error handler


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
        self._disabled: set[str] = set()  # globally disabled command names
        self._disabled_per_server: dict[str, set[str]] = {}  # server_id -> set of cmd names

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
        cooldown_scope: str = "user",
        args: list | None = None,
        public: bool = True,
        requires=None,
    ):
        def decorator(fn: Handler) -> Handler:
            _requires = []
            if requires is not None:
                _requires = list(requires) if hasattr(requires, "__iter__") else [requires]
            # If no explicit args= given, infer converters from type annotations
            _converters = args
            if _converters is None:
                from nerimity_sdk.commands.converters import converters_from_annotations
                _converters = converters_from_annotations(fn)
            cmd = CommandDef(
                name=name, handler=fn, description=description,
                usage=usage, category=category, aliases=aliases or [],
                guild_only=guild_only,
                required_user_perms=required_user_perms or [],
                required_bot_perms=required_bot_perms or [],
                middleware=middleware or [], cooldown=cooldown,
                cooldown_scope=cooldown_scope,
                converters=_converters, public=public,
                requires=_requires,
            )
            self._commands[name] = cmd
            for alias in cmd.aliases:
                self._aliases[alias] = name
            return fn
        return decorator

    def on_error(self, name: str):
        """Decorator: register a per-command error handler.

        Usage::

            @bot.router.on_error("ban")
            async def ban_error(ctx, error):
                await ctx.reply(f"Ban failed: {error}")
        """
        def decorator(fn):
            cmd = self._commands.get(name)
            if cmd:
                cmd.error_handler = fn
            return fn
        return decorator

    def command_private(self, name: str, **kwargs):
        """Register a prefix-only command — never synced to the Nerimity API."""
        return self.command(name, public=False, **kwargs)

    def group(self, name: str, description: str = "") -> "CommandGroup":
        """Create a command group. Subcommands are invoked as `/<group> <sub>`."""
        g = CommandGroup(name=name, description=description, router=self)
        return g

    def use(self, middleware: Middleware) -> None:
        """Register a global middleware applied to every command."""
        self._global_middleware.append(middleware)

    def disable(self, name: str, server_id: str | None = None) -> None:
        """Disable a command globally or for a specific server."""
        if server_id:
            self._disabled_per_server.setdefault(server_id, set()).add(name)
        else:
            self._disabled.add(name)

    def enable(self, name: str, server_id: str | None = None) -> None:
        """Re-enable a previously disabled command."""
        if server_id:
            self._disabled_per_server.get(server_id, set()).discard(name)
        else:
            self._disabled.discard(name)

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
        # Check for group subcommand: "<group> <sub> [args]"
        cmd = None
        if rest:
            sub_parts = rest.split(None, 1)
            group_key = f"{cmd_name} {sub_parts[0].lower()}"
            cmd = self.get_command(group_key)
            if cmd:
                rest = sub_parts[1] if len(sub_parts) > 1 else ""
        if not cmd:
            cmd = self.get_command(cmd_name)
        if not cmd:
            return False

        # Check if command is disabled
        server_disabled = self._disabled_per_server.get(ctx.message.server_id or "", set())
        if cmd.name in self._disabled or cmd.name in server_disabled:
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
            if cmd.cooldown_scope == "server":
                scope_key = ctx.message.server_id or ctx.author.id
            elif cmd.cooldown_scope == "channel":
                scope_key = ctx.channel_id
            else:
                scope_key = ctx.author.id
            key = f"{scope_key}:{cmd.name}"
            last = self._cooldowns.get(key, 0)
            remaining = cmd.cooldown - (time.monotonic() - last)
            if remaining > 0:
                await ctx.reply(f"⏳ You can use `{cmd.name}` again in **{remaining:.1f}s**.")
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

        # requires= shortcut
        if cmd.requires and ctx.server_id:
            from nerimity_sdk.permissions.checker import has_permission
            server = ctx.server
            member = ctx.member
            if server and member:
                for perm in cmd.requires:
                    if not has_permission(member, server, perm):
                        await ctx.reply(f"❌ You need the `{perm.name}` permission to use this command.")
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

        async def run_handler(c: "Context") -> bool:
            await cmd.handler(c)
            return True

        chain = run_handler
        for mw in reversed(all_mw):
            prev = chain
            async def make_next(c: "Context", _mw=mw, _prev=prev) -> bool:
                result = await _mw(c, _prev)
                return result is not False
            chain = make_next

        try:
            await chain(ctx)
        except Exception as exc:
            if cmd.error_handler:
                await cmd.error_handler(ctx, exc)
            else:
                raise
        return True

    def help_text(self, category: Optional[str] = None) -> str:
        """Generate help text from command metadata, including group subcommands."""
        lines = []
        cats: dict[str, list[CommandDef]] = {}
        for cmd in self._commands.values():
            cats.setdefault(cmd.category, []).append(cmd)

        for cat, cmds in sorted(cats.items()):
            if category and cat.lower() != category.lower():
                continue
            lines.append(f"**{cat}**")
            for cmd in sorted(cmds, key=lambda c: c.name):
                aliases = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
                usage = f" `{cmd.usage}`" if cmd.usage else ""
                # Show group subcommands with their full name
                display = f"{self.prefix}{cmd.name}"
                lines.append(f"  `{display}`{usage}{aliases} \u2014 {cmd.description}")
        return "\n".join(lines) or "No commands found."


class CommandGroup:
    """A group of subcommands invoked as `/<group> <sub> [args]`.

    Usage::

        mod = bot.group("mod", description="Moderation commands")

        @mod.command("ban")
        async def mod_ban(ctx): ...

        @mod.command("kick")
        async def mod_kick(ctx): ...
    """
    def __init__(self, name: str, description: str = "",
                 router: "CommandRouter | None" = None) -> None:
        self.name = name
        self.description = description
        self._router = router
        self._subcommands: dict[str, CommandDef] = {}

    def command(self, name: str, **kwargs):
        """Register a subcommand on this group."""
        def decorator(fn):
            sub = CommandDef(
                name=f"{self.name} {name}",
                handler=fn,
                description=kwargs.get("description", ""),
                usage=kwargs.get("usage", ""),
                category=kwargs.get("category", self.name.capitalize()),
                cooldown=kwargs.get("cooldown", 0.0),
                converters=kwargs.get("args") or [],
                public=kwargs.get("public", True),
                requires=kwargs.get("requires") or [],
            )
            self._subcommands[name] = sub
            if self._router:
                self._router._commands[f"{self.name} {name}"] = sub
            return fn
        return decorator