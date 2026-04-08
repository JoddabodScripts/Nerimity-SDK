"""Socket.IO gateway client with auto-reconnect, typed event dispatch, and session resume."""
from __future__ import annotations
import asyncio
from typing import Any, Optional, TYPE_CHECKING
import socketio

if TYPE_CHECKING:
    from nerimity_sdk.events.emitter import EventEmitter

GATEWAY_URL = "https://nerimity.com"

_GATEWAY_EVENTS = [
    "user:authenticated",
    "user:updatedSelf",
    "user:updated",
    "user:presence_update",
    "message:created",
    "message:deleted",
    "message:updated",
    "message:deleted_batch",
    "message:reaction_added",
    "message:reaction_removed",
    "message:button_clicked_callback",
    "server:joined",
    "server:left",
    "server:updated",
    "server:member_joined",
    "server:member_left",
    "server:member_updated",
    "server:channel_created",
    "server:channel_updated",
    "server:channel_deleted",
    "server:role_created",
    "server:role_deleted",
    "server:role_updated",
    "server:role_order_updated",
    "server:channel_order_updated",
    "server:emoji_add",
    "server:emoji_remove",
    "channel:typing",
    "voice:user_joined",
    "voice:user_left",
    "voice:signal_received",
    "friend:request_sent",
    "friend:request_pending",
    "friend:request_accepted",
    "friend:removed",
    "inbox:opened",
    "inbox:closed",
]


class GatewayClient:
    def __init__(self, token: str, emitter: "EventEmitter",
                 shard_id: int = 0, shard_count: int = 1) -> None:
        self._token = token
        self._emitter = emitter
        self._shard_id = shard_id
        self._shard_count = shard_count
        self._sio = socketio.AsyncClient(reconnection=False)
        self._socket_id: Optional[str] = None
        self._running = False
        self._queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
        self._queue_task: Optional[asyncio.Task] = None
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        from nerimity_sdk.utils.logging import get_logger

        @self._sio.event
        async def connect() -> None:
            self._socket_id = self._sio.get_sid()
            get_logger().info(f"[Gateway] Connected (sid={self._socket_id})")
            await self._sio.emit("user:authenticate", {"token": self._token})

        @self._sio.event
        async def disconnect(reason: str) -> None:
            get_logger().warning(f"[Gateway] Disconnected: {reason}")
            await self._queue.put(("_disconnect", None))

        for event in _GATEWAY_EVENTS:
            def make_handler(ev: str):
                async def handler(data: Any = None) -> None:
                    from nerimity_sdk.utils.logging import get_logger
                    get_logger().gateway(ev, data)
                    await self._queue.put((ev, data))
                return handler
            self._sio.on(event, make_handler(event))

    async def _process_queue(self) -> None:
        from nerimity_sdk.events.payloads import deserialize
        while self._running:
            try:
                event, data = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                if event == "_disconnect":
                    await self._emitter.emit("disconnect", None)
                else:
                    typed = deserialize(event, data)
                    await self._emitter.emit(event, typed)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue

    async def connect(self) -> None:
        self._running = True
        self._queue_task = asyncio.create_task(self._process_queue())
        backoff = 1.0
        while self._running:
            try:
                await self._sio.connect(GATEWAY_URL, transports=["websocket"])
                backoff = 1.0
                while self._sio.connected:
                    await asyncio.sleep(0.5)
            except Exception as exc:
                from nerimity_sdk.utils.logging import get_logger
                get_logger().error(f"[Gateway] Connection error: {exc}. Retrying in {backoff:.1f}s")
            if not self._running:
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)

    async def disconnect(self) -> None:
        self._running = False
        if self._sio.connected:
            await self._sio.disconnect()
        if self._queue_task:
            self._queue_task.cancel()
            try:
                await self._queue_task
            except asyncio.CancelledError:
                pass

    async def emit(self, event: str, data: Any = None) -> None:
        await self._sio.emit(event, data)

    @property
    def socket_id(self) -> Optional[str]:
        return self._socket_id
