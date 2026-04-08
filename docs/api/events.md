# Events

## Listening

```python
@bot.on("message:created")
async def handler(event: MessageCreatedEvent): ...

@bot.once("ready")
async def on_first_ready(me: User): ...

@bot.on("*")   # wildcard
async def log_all(data): ...
```

## Typed payload classes

| Event | Payload class | Key fields |
|---|---|---|
| `user:authenticated` | `ReadyEvent` | `.user`, `.servers`, `.channels`, `.members`, `.roles` |
| `message:created` | `MessageCreatedEvent` | `.message`, `.server_id`, `.socket_id` |
| `message:updated` | `MessageUpdatedEvent` | `.channel_id`, `.message_id`, `.updated` |
| `message:deleted` | `MessageDeletedEvent` | `.channel_id`, `.message_id` |
| `message:reaction_added` | `ReactionAddedEvent` | `.message_id`, `.name`, `.count`, `.reacted_by_user_id` |
| `message:reaction_removed` | `ReactionRemovedEvent` | `.message_id`, `.name`, `.count` |
| `server:member_joined` | `MemberJoinedEvent` | `.member`, `.server_id` |
| `server:member_left` | `MemberLeftEvent` | `.server_id`, `.user_id` |
| `server:updated` | `ServerUpdatedEvent` | `.server_id`, `.updated` |
| `server:channel_created` | `ChannelCreatedEvent` | `.channel` |
| `server:channel_updated` | `ChannelUpdatedEvent` | `.channel_id`, `.updated` |
| `server:channel_deleted` | `ChannelDeletedEvent` | `.channel_id` |
| `server:role_created` | `RoleCreatedEvent` | `.role` |
| `server:role_updated` | `RoleUpdatedEvent` | `.role_id`, `.server_id` |
| `server:role_deleted` | `RoleDeletedEvent` | `.role_id`, `.server_id` |
| `user:presence_update` | `PresenceUpdatedEvent` | `.user_id`, `.status`, `.custom` |
| `channel:typing` | `TypingEvent` | `.channel_id`, `.user_id` |

Unknown events fall back to raw dicts — nothing breaks when Nerimity adds new events.

## Error isolation

Each handler runs independently. A crash in one handler does not affect others.
