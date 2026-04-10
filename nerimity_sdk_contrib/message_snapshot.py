"""MessageSnapshotPlugin — logs deleted/edited messages to a channel.

Usage::

    await bot.plugins.load(MessageSnapshotPlugin(log_channel_id="123"))
"""
from nerimity_sdk.plugins.manager import PluginBase, listener
from nerimity_sdk.utils.mentions import mention


class MessageSnapshotPlugin(PluginBase):
    """Logs deleted and edited messages to a channel before they're gone."""
    name = "message_snapshot"

    def __init__(self, log_channel_id: str) -> None:
        super().__init__()
        self.log_channel_id = log_channel_id
        # message_id → last known content
        self._cache: dict[str, str] = {}

    @listener("message:created")
    async def on_create(self, event) -> None:
        from nerimity_sdk.events.payloads import MessageCreatedEvent
        if isinstance(event, MessageCreatedEvent):
            self._cache[event.message.id] = event.message.content or ""

    @listener("message:updated")
    async def on_edit(self, event) -> None:
        from nerimity_sdk.events.payloads import MessageUpdatedEvent
        if not isinstance(event, MessageUpdatedEvent):
            return
        old = self._cache.get(event.message_id, "*(unknown)*")
        new = getattr(event, "content", None) or "*(unknown)*"
        self._cache[event.message_id] = new
        try:
            await self.bot.rest.create_message(
                self.log_channel_id,
                f"✏️ **Message edited** in <#{event.channel_id}>\n"
                f"**Before:** {old}\n**After:** {new}"
            )
        except Exception:
            pass

    @listener("message:deleted")
    async def on_delete(self, event) -> None:
        from nerimity_sdk.events.payloads import MessageDeletedEvent
        if not isinstance(event, MessageDeletedEvent):
            return
        content = self._cache.pop(event.message_id, "*(unknown)*")
        try:
            await self.bot.rest.create_message(
                self.log_channel_id,
                f"🗑️ **Message deleted** in <#{event.channel_id}>\n**Content:** {content}"
            )
        except Exception:
            pass
