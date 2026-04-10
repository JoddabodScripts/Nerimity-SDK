"""HTTP REST client with per-route rate limit buckets and retry-after handling."""
from __future__ import annotations
import asyncio
import time
from typing import Any, Optional
import aiohttp

BASE_URL = "https://nerimity.com/api"


class RateLimitBucket:
    def __init__(self) -> None:
        self.remaining: int = 1
        self.reset_at: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if self.remaining <= 0 and self.reset_at > now:
                wait = self.reset_at - now
                await asyncio.sleep(wait)
            self.remaining = max(0, self.remaining - 1)

    def update(self, headers: dict) -> None:
        if "X-RateLimit-Remaining" in headers:
            self.remaining = int(headers["X-RateLimit-Remaining"])
        if "X-RateLimit-Reset" in headers:
            self.reset_at = float(headers["X-RateLimit-Reset"])


class RESTClient:
    def __init__(self, token: str) -> None:
        self._token = token
        self._session: Optional[aiohttp.ClientSession] = None
        self._buckets: dict[str, RateLimitBucket] = {}
        self._global_lock = asyncio.Lock()
        self._global_reset: float = 0.0
        self.rate_limit_hits: int = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _bucket_key(self, method: str, path: str) -> str:
        # Normalize snowflake IDs so per-route buckets work correctly
        import re
        normalized = re.sub(r"\d{10,}", ":id", path)
        return f"{method}:{normalized}"

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        key = self._bucket_key(method, path)
        bucket = self._buckets.setdefault(key, RateLimitBucket())
        url = f"{BASE_URL}{path}"

        for attempt in range(5):
            # Global rate limit
            async with self._global_lock:
                now = time.monotonic()
                if self._global_reset > now:
                    await asyncio.sleep(self._global_reset - now)

            await bucket.acquire()
            session = await self._get_session()
            req_headers = {
                "Authorization": self._token,
                "Content-Type": "application/json",
            }
            async with session.request(method, url, headers=req_headers, **kwargs) as resp:
                bucket.update(dict(resp.headers))

                if resp.status == 429:
                    data = await resp.json()
                    retry_after = data.get("retry_after", 1.0)
                    self.rate_limit_hits += 1
                    if data.get("global"):
                        self._global_reset = time.monotonic() + retry_after
                    else:
                        bucket.remaining = 0
                        bucket.reset_at = time.monotonic() + retry_after
                    await asyncio.sleep(retry_after)
                    continue

                if resp.status == 403:
                    # Silently return None only for channel message endpoints
                    # (bot lacks permission to speak). Raise for everything else.
                    if "/channels/" in path and "/messages" in path:
                        return None
                    text = await resp.text()
                    raise aiohttp.ClientResponseError(
                        resp.request_info, resp.history,
                        status=resp.status, message=text
                    )

                if resp.status >= 400:
                    text = await resp.text()
                    raise aiohttp.ClientResponseError(
                        resp.request_info, resp.history,
                        status=resp.status, message=text
                    )

                if resp.content_type == "application/json":
                    return await resp.json()
                return await resp.text()

        raise RuntimeError(f"Request {method} {path} failed after 5 attempts")

    async def fetch_user(self, user_id: str) -> dict:
        """Fetch a user by ID from the API."""
        return await self.request("GET", f"/users/{user_id}")

    async def add_roles(self, server_id: str, user_id: str, role_ids: list[str]) -> None:
        """Assign multiple roles to a member in one call (sequential, Nerimity has no bulk endpoint)."""
        import asyncio
        await asyncio.gather(*[
            self.add_role(server_id, user_id, rid) for rid in role_ids
        ])

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # --- Convenience methods ---

    async def create_message(self, channel_id: str, content: str,
                              socket_id: Optional[str] = None,
                              nerimity_file_id: Optional[str] = None,
                              buttons: Optional[list[dict]] = None,
                              embed: Optional[dict] = None) -> dict:
        data: dict = {"content": content, "buttons": []}
        if socket_id:
            data["socketId"] = socket_id
        if nerimity_file_id:
            data["nerimityCdnFileId"] = nerimity_file_id
        if embed:
            data["embed"] = embed
        if buttons:
            for b in buttons:
                data["buttons"].append({
                    "label": str(b["label"]),
                    "id": str(b["id"]),
                    "alert": bool(b.get("alert", False)),
                })
        return await self.request("POST", f"/channels/{channel_id}/messages", json=data)

    async def button_callback(self, channel_id: str, message_id: str,
                               button_id: str, user_id: str,
                               title: str, content: str) -> None:
        """Send a popup response to a button click."""
        await self.request(
            "POST",
            f"/channels/{channel_id}/messages/{message_id}/buttons/{button_id}/callback",
            json={"userId": str(user_id), "title": title, "content": content},
        )

    async def fetch_messages(self, channel_id: str, limit: int = 50,
                              before: Optional[str] = None,
                              after: Optional[str] = None) -> list:
        params: dict = {"limit": limit}
        if before:
            params["before"] = before
        if after:
            params["after"] = after
        return await self.request("GET", f"/channels/{channel_id}/messages", params=params)

    async def delete_message(self, channel_id: str, message_id: str) -> dict:
        return await self.request("DELETE", f"/channels/{channel_id}/messages/{message_id}")

    async def kick_member(self, server_id: str, user_id: str) -> dict:
        return await self.request("DELETE", f"/servers/{server_id}/members/{user_id}/kick")

    async def ban_member(self, server_id: str, user_id: str,
                          delete_recent_messages: bool = False) -> dict:
        params = {"shouldDeleteRecentMessages": str(delete_recent_messages).lower()}
        return await self.request("POST", f"/servers/{server_id}/bans/{user_id}", params=params)

    async def unban_member(self, server_id: str, user_id: str) -> dict:
        return await self.request("DELETE", f"/servers/{server_id}/bans/{user_id}")

    async def update_role(self, server_id: str, role_id: str, **fields: Any) -> dict:
        body = {k: v for k, v in {
            "name": fields.get("name"),
            "hexColor": fields.get("hex_color"),
            "hideRole": fields.get("hide_role"),
            "permissions": fields.get("permissions"),
        }.items() if v is not None}
        return await self.request("POST", f"/servers/{server_id}/roles/{role_id}", json=body)

    async def delete_role(self, server_id: str, role_id: str) -> dict:
        return await self.request("DELETE", f"/servers/{server_id}/roles/{role_id}")

    async def upload_file(self, path: str) -> str:
        """Upload a file to Nerimity CDN. Returns the fileId string."""
        import aiohttp as _aiohttp
        cdn_url = "https://cdn.nerimity.com/upload"
        session = await self._get_session()
        with open(path, "rb") as f:
            data = _aiohttp.FormData()
            import os
            data.add_field("file", f, filename=os.path.basename(path))
            async with session.post(cdn_url, data=data,
                                    headers={"Authorization": self._token}) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise RuntimeError(f"CDN upload failed ({resp.status}): {text}")
                result = await resp.json()
                return result["fileId"]

    async def open_dm(self, user_id: str) -> dict:
        """Open (or retrieve) a DM channel with a user. Returns the Channel."""
        return await self.request("POST", f"/users/{user_id}/open-channel")

    async def bulk_delete_messages(self, channel_id: str, message_ids: list[str]) -> None:
        """Delete multiple messages. Falls back to sequential deletes if no bulk endpoint."""
        import asyncio
        await asyncio.gather(*[
            self.delete_message(channel_id, mid) for mid in message_ids
        ])

    async def register_bot_commands(self, commands: list[dict]) -> dict:
        return await self.request("POST", "/applications/bot/commands", json={"commands": commands})

    async def add_reaction(self, channel_id: str, message_id: str, name: str,
                            emoji_id: Optional[str] = None,
                            gif: bool = False, webp: bool = False) -> dict:
        body: dict = {"name": name}
        if emoji_id:
            body["emojiId"] = emoji_id
        if gif:
            body["gif"] = True
        if webp:
            body["webp"] = True
        return await self.request(
            "POST", f"/channels/{channel_id}/messages/{message_id}/reactions", json=body
        )

    async def remove_reaction(self, channel_id: str, message_id: str, name: str,
                               emoji_id: Optional[str] = None) -> dict:
        body: dict = {"name": name}
        if emoji_id:
            body["emojiId"] = emoji_id
        return await self.request(
            "POST", f"/channels/{channel_id}/messages/{message_id}/reactions/remove", json=body
        )

    async def fetch_reaction_users(self, channel_id: str, message_id: str, name: str,
                                    emoji_id: Optional[str] = None, limit: int = 50) -> list:
        params: dict = {"name": name, "limit": limit}
        if emoji_id:
            params["emojiId"] = emoji_id
        return await self.request(
            "GET", f"/channels/{channel_id}/messages/{message_id}/reactions/users", params=params
        )

    async def update_message(self, channel_id: str, message_id: str, content: str,
                              buttons: Optional[list[dict]] = None) -> dict:
        body: dict = {"content": content}
        if buttons is not None:
            body["buttons"] = buttons
        return await self.request(
            "PATCH", f"/channels/{channel_id}/messages/{message_id}", json=body
        )

    async def add_role(self, server_id: str, user_id: str, role_id: str) -> dict:
        return await self.request(
            "POST", f"/servers/{server_id}/members/{user_id}/roles/{role_id}"
        )

    async def remove_role(self, server_id: str, user_id: str, role_id: str) -> dict:
        return await self.request(
            "DELETE", f"/servers/{server_id}/members/{user_id}/roles/{role_id}"
        )

    async def pin_message(self, channel_id: str, message_id: str) -> dict:
        return await self.request("POST", f"/channels/{channel_id}/messages/pins/{message_id}")

    async def unpin_message(self, channel_id: str, message_id: str) -> dict:
        return await self.request("DELETE", f"/channels/{channel_id}/messages/pins/{message_id}")

    async def send_typing(self, channel_id: str) -> None:
        await self.request("POST", f"/channels/{channel_id}/typing")

    async def join_voice(self, channel_id: str, socket_id: str) -> dict:
        return await self.request("POST", f"/channels/{channel_id}/voice/join",
                                   json={"socketId": socket_id})

    async def leave_voice(self, channel_id: str) -> dict:
        return await self.request("POST", f"/channels/{channel_id}/voice/leave")
