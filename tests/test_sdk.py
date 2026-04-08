"""Unit tests for nerimity-sdk — no real network connection required."""
import asyncio
import pytest
from nerimity_sdk.testing import MockBot, make_context, make_user
from nerimity_sdk.cache.store import Cache
from nerimity_sdk.commands.router import CommandRouter, _parse_args
from nerimity_sdk.commands.builders import Embed, MessageBuilder
from nerimity_sdk.events.emitter import EventEmitter
from nerimity_sdk.events.payloads import (
    MessageCreatedEvent, ReactionAddedEvent, MemberJoinedEvent,
    ReadyEvent, deserialize,
)
from nerimity_sdk.models import Permissions, Role, Server, Member, Message, User
from nerimity_sdk.permissions.checker import has_permission, resolve_permissions
from nerimity_sdk.storage import MemoryStore, JsonStore
from nerimity_sdk.commands.prefix import PrefixResolver


# ── Argument parsing ──────────────────────────────────────────────────────────

def test_parse_args_basic():
    args, flags = _parse_args("hello world")
    assert args == ["hello", "world"]
    assert flags == {}


def test_parse_args_flags():
    args, flags = _parse_args('--silent --count=3 "quoted arg"')
    assert flags["silent"] is True
    assert flags["count"] == "3"
    assert args == ["quoted arg"]


# ── Typed event payloads ──────────────────────────────────────────────────────

def test_deserialize_message_created():
    raw = {
        "socketId": "abc",
        "serverId": "s1",
        "message": {
            "id": "1", "channelId": "c1", "type": 0, "content": "hi",
            "createdBy": {"id": "u1", "username": "Alice", "tag": "0001", "hexColor": ""},
            "createdAt": 0, "reactions": [], "quotedMessages": [],
            "replyMessages": [], "buttons": [], "roleMentions": [],
        }
    }
    event = deserialize("message:created", raw)
    assert isinstance(event, MessageCreatedEvent)
    assert event.message.content == "hi"
    assert event.server_id == "s1"


def test_deserialize_reaction_added():
    raw = {"messageId": "1", "channelId": "c1", "count": 2,
           "reactedByUserId": "u1", "name": "👍"}
    event = deserialize("message:reaction_added", raw)
    assert isinstance(event, ReactionAddedEvent)
    assert event.count == 2
    assert event.name == "👍"


def test_deserialize_unknown_event_passthrough():
    raw = {"foo": "bar"}
    result = deserialize("some:unknown_event", raw)
    assert result == raw  # raw dict passed through unchanged


def test_deserialize_ready():
    raw = {
        "user": {"id": "1", "username": "Bot", "tag": "0000", "hexColor": ""},
        "servers": [], "channels": [], "serverMembers": [], "serverRoles": [],
    }
    event = deserialize("user:authenticated", raw)
    assert isinstance(event, ReadyEvent)
    assert event.user.username == "Bot"


# ── Event emitter ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_event_emitter_on():
    emitter = EventEmitter()
    received = []
    async def handler(data):
        received.append(data)
    emitter.on("test", handler)
    await emitter.emit("test", 42)
    assert received == [42]


@pytest.mark.asyncio
async def test_event_emitter_once():
    emitter = EventEmitter()
    received = []
    async def handler(data):
        received.append(data)
    emitter.once("test", handler)
    await emitter.emit("test", 1)
    await emitter.emit("test", 2)
    assert received == [1]


@pytest.mark.asyncio
async def test_event_emitter_wildcard():
    emitter = EventEmitter()
    received = []
    async def handler(data):
        received.append(data)
    emitter.on("*", handler)
    await emitter.emit("anything", "x")
    assert "x" in received


@pytest.mark.asyncio
async def test_event_handler_error_isolation():
    emitter = EventEmitter()
    results = []
    async def bad(data):
        raise RuntimeError("boom")
    async def good(data):
        results.append(data)
    emitter.on("ev", bad)
    emitter.on("ev", good)
    await emitter.emit("ev", "ok")
    assert results == ["ok"]


# ── Cache ─────────────────────────────────────────────────────────────────────

def test_cache_upsert_user_merge():
    cache = Cache()
    cache.upsert_user({"id": "1", "username": "Alice", "tag": "0001", "hexColor": "#fff"})
    cache.upsert_user({"id": "1", "username": "AliceUpdated", "tag": "0001", "hexColor": "#fff"})
    user = cache.users.get("1")
    assert user.username == "AliceUpdated"


def test_cache_lru_eviction():
    from nerimity_sdk.cache.store import LRUCache
    c = LRUCache(max_size=2)
    c.set("a", 1)
    c.set("b", 2)
    c.set("c", 3)
    assert c.get("a") is None
    assert c.get("b") == 2


# ── Permissions ───────────────────────────────────────────────────────────────

def _make_server_with_role(perms: Permissions) -> tuple[Server, Member]:
    role = Role(id="r1", server_id="s1", created_by_id="0", order=1,
                bot_role=False, hex_color="", name="mod", hide_role=False,
                created_at="", permissions=perms)
    server = Server(id="s1", name="Test", created_by_id="0")
    server.roles["r1"] = role
    user = make_user()
    member = Member(user=user, server_id="s1", role_ids=["r1"])
    return server, member


def test_has_permission_true():
    server, member = _make_server_with_role(Permissions.KICK_MEMBERS)
    assert has_permission(member, server, Permissions.KICK_MEMBERS)


def test_has_permission_false():
    server, member = _make_server_with_role(Permissions.SEND_MESSAGES)
    assert not has_permission(member, server, Permissions.KICK_MEMBERS)


def test_admin_bypasses_all():
    server, member = _make_server_with_role(Permissions.ADMIN)
    assert has_permission(member, server, Permissions.BAN_MEMBERS)


# ── Builders ──────────────────────────────────────────────────────────────────

def test_embed_builder():
    embed = Embed().title("Hello").description("World").color(0xff0000)
    d = embed.to_dict()
    assert d["title"] == "Hello"
    assert d["description"] == "World"
    assert d["hexColor"] == "#ff0000"


def test_message_builder():
    body = (MessageBuilder()
            .content("hi")
            .reply_to("msg1", "msg2")
            .silent()
            .build())
    assert body["content"] == "hi"
    assert body["replyToMessageIds"] == ["msg1", "msg2"]
    assert body["silent"] is True


# ── Per-guild prefix ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_prefix_resolver_default():
    resolver = PrefixResolver(default="!")
    assert await resolver.resolve(None) == "!"
    assert await resolver.resolve("guild1") == "!"


@pytest.mark.asyncio
async def test_prefix_resolver_custom():
    resolver = PrefixResolver(default="!")
    await resolver.set("guild1", "?")
    assert await resolver.resolve("guild1") == "?"
    assert await resolver.resolve("guild2") == "!"


# ── Storage ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_memory_store():
    store = MemoryStore()
    await store.set("key", {"value": 42})
    assert await store.get("key") == {"value": 42}
    await store.delete("key")
    assert await store.get("key") is None


@pytest.mark.asyncio
async def test_json_store(tmp_path):
    path = str(tmp_path / "test.json")
    store = JsonStore(path)
    await store.set("x", 99)
    # Reload from disk
    store2 = JsonStore(path)
    assert await store2.get("x") == 99


@pytest.mark.asyncio
async def test_store_keys_pattern():
    store = MemoryStore()
    await store.set("guild:1:prefix", "!")
    await store.set("guild:2:prefix", "?")
    await store.set("other:key", "x")
    keys = await store.keys("guild:*")
    assert set(keys) == {"guild:1:prefix", "guild:2:prefix"}


# ── Command router ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_command_dispatch():
    bot = MockBot(prefix="!")
    results = []

    @bot.command("ping")
    async def ping(ctx):
        results.append("pong")

    await bot.simulate_message("!ping")
    assert results == ["pong"]


@pytest.mark.asyncio
async def test_command_args():
    bot = MockBot(prefix="!")
    captured = {}

    @bot.command("echo")
    async def echo(ctx):
        captured["args"] = ctx.args
        captured["flags"] = ctx.flags

    await bot.simulate_message('!echo hello world --shout')
    assert captured["args"] == ["hello", "world"]
    assert captured["flags"]["shout"] is True


@pytest.mark.asyncio
async def test_command_cooldown():
    bot = MockBot(prefix="!")
    replies = []
    bot.rest.create_message.side_effect = lambda ch, content: replies.append(content) or \
        {"id": "1", "channelId": ch, "type": 0, "content": content,
         "createdBy": {"id": "0", "username": "B", "tag": "0000", "hexColor": ""}, "createdAt": 0}

    @bot.command("slow", cooldown=60.0)
    async def slow(ctx):
        replies.append("ok")

    await bot.simulate_message("!slow")
    await bot.simulate_message("!slow")
    assert replies.count("ok") == 1


# ── ctx.react() ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ctx_react():
    bot = MockBot(prefix="!")

    @bot.command("like")
    async def like(ctx):
        await ctx.react("👍")

    await bot.simulate_message("!like")
    bot.rest.add_reaction.assert_called_once()
    call_kwargs = bot.rest.add_reaction.call_args
    assert call_kwargs.kwargs["name"] == "👍"


# ── ctx.ask() ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ctx_ask():
    bot = MockBot(prefix="!")
    answers = []

    @bot.command("name")
    async def ask_name(ctx):
        reply = await ctx.ask("What's your name?", timeout=2.0)
        answers.append(reply.content if reply else None)

    # Simulate the command, then the follow-up answer
    async def _run():
        task = asyncio.create_task(bot.simulate_message("!name", author_id="42"))
        await asyncio.sleep(0.05)  # let the ask() register its listener
        await bot.simulate_message("Alice", author_id="42")
        await task

    await _run()
    assert answers == ["Alice"]


@pytest.mark.asyncio
async def test_ctx_ask_timeout():
    bot = MockBot(prefix="!")
    answers = []

    @bot.command("silent")
    async def ask_silent(ctx):
        reply = await ctx.ask("Say something", timeout=0.1)
        answers.append(reply)

    await bot.simulate_message("!silent")
    await asyncio.sleep(0.2)
    assert answers == [None]


# ── Plugin system ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_plugin_load_unload():
    from nerimity_sdk.plugins.manager import PluginBase, listener

    bot = MockBot()
    events = []

    class MyPlugin(PluginBase):
        name = "test_plugin"

        @listener("server:member_joined")
        async def on_join(self, data):
            events.append(data)

    plugin = MyPlugin()
    await bot.plugins.load(plugin)
    assert "test_plugin" in bot.plugins.loaded

    await bot.simulate_event("server:member_joined", {"userId": "42", "serverId": "s1"})
    assert len(events) == 1
    assert isinstance(events[0], MemberJoinedEvent)

    await bot.plugins.unload("test_plugin")
    assert "test_plugin" not in bot.plugins.loaded
