"""
nerimity-sdk-contrib
====================
Ready-made plugins for nerimity-sdk bots.

Usage::

    pip install nerimity-sdk-contrib

    from nerimity_sdk_contrib import WelcomePlugin, AutoModPlugin, StarboardPlugin, LoggingPlugin

    await bot.plugins.load(WelcomePlugin(channel_id="123"))
    await bot.plugins.load(AutoModPlugin(blocked=["badword"]))
    await bot.plugins.load(StarboardPlugin(channel_id="456", threshold=3))
    await bot.plugins.load(LoggingPlugin(channel_id="789"))

Adding a new plugin
-------------------
1. Create nerimity_sdk_contrib/your_plugin.py with a class inheriting PluginBase
2. Import and re-export it here
3. Add it to the docs/plugins.md marketplace table
"""
from nerimity_sdk_contrib.welcome import WelcomePlugin
from nerimity_sdk_contrib.automod import AutoModPlugin
from nerimity_sdk_contrib.starboard import StarboardPlugin
from nerimity_sdk_contrib.server_logging import LoggingPlugin
from nerimity_sdk_contrib.role_menu import RoleMenuPlugin
from nerimity_sdk_contrib.poll import PollPlugin
from nerimity_sdk_contrib.antispam import AntiSpamPlugin
from nerimity_sdk_contrib.leveling import LevelingPlugin
from nerimity_sdk_contrib.tickets import TicketPlugin
from nerimity_sdk_contrib.giveaway import GiveawayPlugin
from nerimity_sdk_contrib.reminders import ReminderPlugin
from nerimity_sdk_contrib.translate import TranslatePlugin
from nerimity_sdk_contrib.autorole import AutoRolePlugin
from nerimity_sdk_contrib.reaction_roles import ReactionRolesPlugin
from nerimity_sdk_contrib.birthday import BirthdayPlugin
from nerimity_sdk_contrib.counter import CounterPlugin
from nerimity_sdk_contrib.moderation_log import ModerationLogPlugin
from nerimity_sdk_contrib.slowmode import SlowmodePlugin
from nerimity_sdk_contrib.afk import AFKPlugin
from nerimity_sdk_contrib.suggestions import SuggestionPlugin
from nerimity_sdk_contrib.warn import WarnPlugin
from nerimity_sdk_contrib.message_filter import MessageFilterPlugin
from nerimity_sdk_contrib.message_snapshot import MessageSnapshotPlugin

__version__ = "1.0.8"

__all__ = [
    "WelcomePlugin",
    "AutoModPlugin",
    "StarboardPlugin",
    "LoggingPlugin",
    "RoleMenuPlugin",
    "PollPlugin",
    "AntiSpamPlugin",
    "LevelingPlugin",
    "TicketPlugin",
    "GiveawayPlugin",
    "ReminderPlugin",
    "TranslatePlugin",
    "AutoRolePlugin",
    "ReactionRolesPlugin",
    "BirthdayPlugin",
    "CounterPlugin",
    "ModerationLogPlugin",
    "SlowmodePlugin",
    "AFKPlugin",
    "SuggestionPlugin",
    "WarnPlugin",
    "MessageFilterPlugin",
    "MessageSnapshotPlugin",
]
