"""Permission system: flag mapping, role hierarchy, and declarative checks."""
from __future__ import annotations
from typing import TYPE_CHECKING
from nerimity_sdk.models import Permissions

if TYPE_CHECKING:
    from nerimity_sdk.models import Member, Server


PERMISSION_NAMES: dict[str, Permissions] = {
    "admin": Permissions.ADMIN,
    "send_messages": Permissions.SEND_MESSAGES,
    "manage_roles": Permissions.MANAGE_ROLES,
    "kick_members": Permissions.KICK_MEMBERS,
    "ban_members": Permissions.BAN_MEMBERS,
    "manage_channels": Permissions.MANAGE_CHANNELS,
    "manage_server": Permissions.MANAGE_SERVER,
}


def resolve_permissions(member: "Member", server: "Server") -> Permissions:
    """Compute the combined permissions for a member from all their roles."""
    perms = Permissions.NONE
    for role_id in member.role_ids:
        role = server.roles.get(role_id)
        if role:
            perms |= role.permissions
    return perms


def has_permission(member: "Member", server: "Server", *required: Permissions) -> bool:
    perms = resolve_permissions(member, server)
    if Permissions.ADMIN in perms:
        return True
    return all(p in perms for p in required)


def role_position(member: "Member", server: "Server") -> int:
    """Return the highest role order for a member (higher = more powerful)."""
    positions = [
        server.roles[rid].order
        for rid in member.role_ids
        if rid in server.roles
    ]
    return max(positions, default=0)


def can_target(actor: "Member", target: "Member", server: "Server") -> bool:
    """True if actor's highest role is above target's (for kick/ban)."""
    return role_position(actor, server) > role_position(target, server)
