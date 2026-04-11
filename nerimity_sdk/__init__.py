"""nerimity-sdk — A fully-featured Python SDK for building Nerimity bots."""
from nerimity_sdk.bot import Bot, __version__
from nerimity_sdk.models import (
    User, UserBadge, Message, MessageAttachment,
    Server, Channel, Member, Role, BotCommand, Permissions,
)
from nerimity_sdk.context.ctx import Context
from nerimity_sdk.commands.converters import Int, Member as MemberConverter, User as UserConverter, Channel as ChannelConverter, ConversionError, Float, Bool
from nerimity_sdk.commands.router import CommandRouter, CommandGroup
from nerimity_sdk.events.emitter import EventEmitter
from nerimity_sdk.events.payloads import (
    ReadyEvent, MessageCreatedEvent, MessageUpdatedEvent, MessageDeletedEvent,
    ReactionAddedEvent, ReactionRemovedEvent, MemberJoinedEvent, MemberLeftEvent,
    PresenceUpdatedEvent, TypingEvent,
)
from nerimity_sdk.cache.store import Cache
from nerimity_sdk.permissions.checker import (
    has_permission, resolve_permissions, role_position, can_target,
)
from nerimity_sdk.plugins.manager import PluginBase, PluginManager, listener
from nerimity_sdk.storage import JsonStore, SqliteStore, RedisStore, MemoryStore
from nerimity_sdk.scheduler import Scheduler, CronJob
from nerimity_sdk.utils.mentions import mention, parse_mention_ids, resolve_mentions
from nerimity_sdk.utils.paginator import Paginator
from nerimity_sdk.utils.embed import Embed
from nerimity_sdk.webhooks import Webhook
from nerimity_sdk.oauth2 import OAuth2Client

__all__ = [
    "__version__",
    "Bot",
    # Models
    "User", "UserBadge", "Message", "MessageAttachment",
    "Server", "Channel", "Member", "Role", "BotCommand", "Permissions",
    # Context
    "Context",
    # Commands
    "CommandRouter", "CommandGroup", "MessageBuilder", "Embed",
    "PrefixResolver", "MemoryPrefixStore",
    "SlashRouter", "SlashContext",
    "Button", "ComponentRow", "ButtonRouter", "ButtonContext",
    "Int", "Float", "Bool", "MemberConverter", "UserConverter", "ChannelConverter", "ConversionError",
    # Events
    "EventEmitter",
    "ReadyEvent", "MessageCreatedEvent", "MessageUpdatedEvent", "MessageDeletedEvent",
    "ReactionAddedEvent", "ReactionRemovedEvent", "MemberJoinedEvent", "MemberLeftEvent",
    "PresenceUpdatedEvent", "TypingEvent",
    # Cache
    "Cache",
    # Permissions
    "has_permission", "resolve_permissions", "role_position", "can_target",
    # Plugins
    "PluginBase", "PluginManager", "listener",
    # Storage
    "JsonStore", "SqliteStore", "RedisStore", "MemoryStore",
    # Scheduler
    "Scheduler", "CronJob",
    # Utils
    "mention", "parse_mention_ids", "resolve_mentions",
    "Paginator",
    # Webhooks & OAuth2
    "Webhook", "OAuth2Client",
]
