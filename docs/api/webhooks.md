# Webhooks

Webhooks let you send messages to a Nerimity channel without a running bot — useful for notifications from external services, CI/CD pipelines, or any script.

## Install

```
pip install nerimity-sdk
```

## Send a message

```python
import asyncio
from nerimity_sdk import Webhook

async def main():
    wh = Webhook("YOUR_WEBHOOK_TOKEN")
    await wh.send("Hello from a webhook! 👋")

asyncio.run(main())
```

## Send an embed

```python
from nerimity_sdk import Webhook, Embed

async def main():
    wh = Webhook("YOUR_WEBHOOK_TOKEN")
    embed = (
        Embed()
        .title("Deployment complete ✅")
        .description("Version **1.4.2** is now live.")
        .field("Branch", "main", inline=True)
        .field("Duration", "42s", inline=True)
        .color("#a78bfa")
    )
    await wh.send(embed=embed)
```

## Send a file

```python
await wh.send("Here's the log:", file="build.log")
```

## Getting a webhook token

1. Go to the channel settings in Nerimity
2. Open the **Webhooks** tab
3. Click **Create Webhook** and copy the token

## Reference

| Method | Description |
|---|---|
| `Webhook(token)` | Create a webhook client |
| `await wh.send(content)` | Send a plain text message |
| `await wh.send(embed=embed)` | Send an embed |
| `await wh.send(file="path")` | Send a file |
| `await wh.send(content, embed=embed, file="path")` | Combine all three |
