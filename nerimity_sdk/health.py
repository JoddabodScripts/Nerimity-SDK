"""Lightweight HTTP health/stats server.

Exposes two endpoints:
  GET /health  → {"status": "ok", "uptime": 123.4}
  GET /stats   → full bot.stats dict as JSON

Usage::

    bot = Bot(token="...", health_port=8080)
"""
from __future__ import annotations
import asyncio
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nerimity_sdk.bot import Bot


class HealthServer:
    def __init__(self, bot: "Bot", port: int) -> None:
        self._bot = bot
        self._port = port
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle, "0.0.0.0", self._port
        )
        self._bot.logger.info(f"[Health] Listening on :{self._port}")

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader,
                      writer: asyncio.StreamWriter) -> None:
        try:
            request = (await reader.read(256)).decode(errors="ignore")
            path = request.split(" ")[1] if " " in request else "/"

            if path == "/health":
                body = json.dumps({"status": "ok",
                                   "uptime": self._bot.stats["uptime_seconds"]})
            elif path == "/stats":
                body = json.dumps(self._bot.stats)
            else:
                writer.write(b"HTTP/1.1 404 Not Found\r\n\r\n")
                await writer.drain()
                writer.close()
                return

            response = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"\r\n{body}"
            )
            writer.write(response.encode())
            await writer.drain()
        finally:
            writer.close()
