# Permissions

## Permission flags

```python
from nerimity_sdk import Permissions

Permissions.ADMIN
Permissions.SEND_MESSAGES
Permissions.MANAGE_ROLES
Permissions.KICK_MEMBERS
Permissions.BAN_MEMBERS
Permissions.MANAGE_CHANNELS
Permissions.MANAGE_SERVER
```

## Checking permissions

```python
from nerimity_sdk import has_permission, resolve_permissions

# True if member has the permission (admin bypasses all)
if has_permission(member, server, Permissions.KICK_MEMBERS):
    ...

# Get combined permission bits for a member
perms = resolve_permissions(member, server)
```

## Role hierarchy

```python
from nerimity_sdk import role_position, can_target

# Highest role order for a member
pos = role_position(member, server)

# True if actor's highest role is above target's
if can_target(actor_member, target_member, server):
    await ctx.rest.kick_member(server_id, target_id)
```

## Per-command permissions

```python
@bot.command("ban", required_user_perms=[Permissions.BAN_MEMBERS])
async def ban(ctx):
    ...  # only runs if user has BAN_MEMBERS
```
