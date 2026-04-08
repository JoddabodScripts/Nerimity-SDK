"""Plugin/module system with hot reload and lifecycle hooks."""
from __future__ import annotations
import importlib
import importlib.util
import sys
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from nerimity_sdk.bot import Bot


class Plugin:
    """Base class for all plugins. Override lifecycle hooks as needed."""

    name: str = ""
    description: str = ""

    def __init__(self) -> None:
        self._bot: Optional["Bot"] = None

    @property
    def bot(self) -> "Bot":
        assert self._bot is not None, "Plugin not attached to a bot"
        return self._bot

    async def on_load(self) -> None:
        """Called when the plugin is loaded."""

    async def on_unload(self) -> None:
        """Called before the plugin is unloaded."""

    async def on_ready(self) -> None:
        """Called when the bot is ready (after authentication)."""


class PluginManager:
    def __init__(self, bot: "Bot") -> None:
        self._bot = bot
        self._plugins: dict[str, Plugin] = {}

    async def load(self, plugin: Plugin) -> None:
        name = plugin.name or type(plugin).__name__
        if name in self._plugins:
            raise ValueError(f"Plugin {name!r} is already loaded")
        plugin._bot = self._bot
        # Register the plugin's commands and listeners
        self._bot.router._commands.update(
            getattr(plugin, "_commands", {})
        )
        # Bind unbound methods to the plugin instance before registering
        plugin._bound_listeners: dict[str, list] = {}
        for event, handlers in getattr(plugin, "_listeners", {}).items():
            bound = []
            for handler in handlers:
                import functools
                b = functools.partial(handler, plugin)
                b.__name__ = getattr(handler, "__name__", repr(handler))  # type: ignore
                bound.append(b)
                self._bot.emitter.on(event, b)
            plugin._bound_listeners[event] = bound
        self._plugins[name] = plugin
        await plugin.on_load()
        self._bot.logger.info(f"[Plugin] Loaded: {name}")

    async def unload(self, name: str) -> None:
        plugin = self._plugins.pop(name, None)
        if not plugin:
            raise KeyError(f"Plugin {name!r} not loaded")
        await plugin.on_unload()
        # Remove plugin's commands
        for cmd_name in list(getattr(plugin, "_commands", {}).keys()):
            self._bot.router._commands.pop(cmd_name, None)
        # Remove plugin's bound listeners
        for event, bound_handlers in getattr(plugin, "_bound_listeners", {}).items():
            for handler in bound_handlers:
                self._bot.emitter.off(event, handler)
        self._bot.logger.info(f"[Plugin] Unloaded: {name}")

    async def reload(self, name: str) -> None:
        plugin = self._plugins.get(name)
        if not plugin:
            raise KeyError(f"Plugin {name!r} not loaded")
        module_name = type(plugin).__module__
        await self.unload(name)
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        # Re-instantiate from reloaded module
        mod = sys.modules[module_name]
        cls = type(plugin)
        new_plugin = getattr(mod, cls.__name__)()
        await self.load(new_plugin)

    async def load_from_path(self, path: str) -> None:
        """Load a plugin from a file path."""
        spec = importlib.util.spec_from_file_location("_plugin_module", path)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load plugin from {path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        setup = getattr(mod, "setup", None)
        if not setup:
            raise AttributeError(f"Plugin at {path} must define a setup(bot) function")
        await setup(self._bot)

    async def dispatch_ready(self) -> None:
        for plugin in self._plugins.values():
            await plugin.on_ready()

    @property
    def loaded(self) -> list[str]:
        return list(self._plugins.keys())


def listener(event: str):
    """Decorator to register a method as an event listener on a Plugin subclass."""
    def decorator(fn):
        if not hasattr(fn, "_listener_events"):
            fn._listener_events = []
        fn._listener_events.append(event)
        return fn
    return decorator


class PluginMeta(type):
    """Metaclass that collects @listener-decorated methods into _listeners."""
    def __new__(mcs, name, bases, namespace):
        listeners: dict[str, list] = {}
        commands: dict = {}
        for val in namespace.values():
            for event in getattr(val, "_listener_events", []):
                listeners.setdefault(event, []).append(val)
        namespace["_listeners"] = listeners
        namespace["_commands"] = commands
        return super().__new__(mcs, name, bases, namespace)


class PluginBase(Plugin, metaclass=PluginMeta):
    """Convenience base class combining Plugin + PluginMeta."""
