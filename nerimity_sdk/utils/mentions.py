"""Mention parsing utilities for Nerimity's [@:id] format."""
from __future__ import annotations
import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from nerimity_sdk.models import User
    from nerimity_sdk.cache.store import Cache

_MENTION_RE = re.compile(r"\[@:(\d+)\]")


def parse_mention_ids(content: str) -> list[str]:
    """Extract all user IDs from [@:id] mentions in a string."""
    return _MENTION_RE.findall(content)


def mention(user_id: str) -> str:
    """Format a user ID as a Nerimity mention: [@:id]"""
    return f"[@:{user_id}]"


def resolve_mentions(content: str, cache: "Cache") -> list["User"]:
    """Parse [@:id] mentions and resolve each to a cached User (skips misses)."""
    users = []
    for uid in parse_mention_ids(content):
        user = cache.users.get(uid)
        if user:
            users.append(user)
    return users
