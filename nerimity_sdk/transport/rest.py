"""HTTP REST client with per-route rate limit buckets and retry-after handling."""
from __future__ import annotations
import asyncio
import time
from typing import Any, Optional
import aiohttp

from .ratelimit import RateLimitBackend, LocalRateLimitBackend

BASE_URL = "https://nerimity.com/api"


class RESTClient:
    def __init__(self, token: str, rate_limiter: Optional[RateLimitBackend] = None) -> None:
        self._token = token
        self._session: Optional[aiohttp.ClientSession] = None
        self._rl: RateLimitBackend = rate_limiter or LocalRateLimitBackend()
        self.rate_limit_hits: int = 0
        self._ratelimit_callback = None
        self.timeout: float = 30.0

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _bucket_key(self, method: str, path: str) -> str:
        import re
        normalized = re.sub(r"\d{10,}", ":id", path)
        return f"{method}:{normalized}"

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        key = self._bucket_key(method, path)
        url = f"{BASE_URL}{path}"

        for attempt in range(5):
            await self._rl.acquire_global()
            await self._rl.acquire(key)

            session = await self._get_session()
            req_headers = {
                "Authorization": self._token,
                "Content-Type": "application/json",
            }
            async with session.request(method, url, headers=req_headers,
                                       timeout=aiohttp.ClientTimeout(total=self.timeout),
                                       **kwargs) as resp:
                headers = dict(resp.headers)
                if "X-RateLimit-Remaining" in headers and "X-RateLimit-Reset" in headers:
                    await self._rl.update(
                        key,
                        int(headers["X-RateLimit-Remaining"]),
                        float(headers["X-RateLimit-Reset"]),
                    )

                if resp.status == 429:
                    data = await resp.json()
                    retry_after = data.get("retry_after", 1.0)
                    self.rate_limit_hits += 1
                    if self._ratelimit_callback:
                        try:
                            await self._ratelimit_callback(path, retry_after)
                        except Exception:
                            pass
                    if data.get("global"):
                        await self._rl.set_global_reset(time.time() + retry_after)
                    else:
                        await self._rl.update(key, 0, time.time() + retry_after)
                    await asyncio.sleep(retry_after)
                    continue

                if resp.status == 403:
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

    async def fetch_server_members(self, server_id: str) -> list:
        """Fetch all members of a server."""
        return await self.request("GET", f"/servers/{server_id}/members")

    async def create_role(self, server_id: str, name: str,
                          hex_color: str = "", permissions: int = 0,
                          hide_role: bool = False) -> dict:
        """Create a new role in a server."""
        return await self.request("POST", f"/servers/{server_id}/roles", json={
            "name": name,
            "hexColor": hex_color,
            "permissions": permissions,
            "hideRole": hide_role,
        })

    async def set_nickname(self, server_id: str, user_id: str,
                       nickname: str | None) -> dict:
        """Set or clear a member's nickname. Pass None to clear."""
        return await self.request(
            "PATCH", f"/servers/{server_id}/members/{user_id}",
            json={"nickname": nickname},
        )

    async def fetch_bans(self, server_id: str) -> list:
        """Fetch the list of banned users for a server."""
        return await self.request("GET", f"/servers/{server_id}/bans")

    async def create_channel(self, server_id: str, name: str,
                              channel_type: int = 0) -> dict:
        """Create a new channel in a server."""
        return await self.request(
            "POST", f"/servers/{server_id}/channels",
            json={"name": name, "type": channel_type},
        )

    async def delete_channel(self, channel_id: str) -> dict:
        """Delete a channel."""
        return await self.request("DELETE", f"/channels/{channel_id}")

    async def fetch_message(self, channel_id: str, message_id: str) -> dict:
        """Fetch a single message by ID."""
        return await self.request("GET", f"/channels/{channel_id}/messages/{message_id}")

    async def fetch_server(self, server_id: str) -> dict:
        """Fetch server info from the API."""
        return await self.request("GET", f"/servers/{server_id}")

    async def fetch_channel(self, channel_id: str) -> dict:
        """Fetch a channel by ID from the API."""
        return await self.request("GET", f"/channels/{channel_id}")

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        await self._rl.close()

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
