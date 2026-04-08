# Scheduler

Run tasks on a cron schedule. Requires `pip install croniter`.

## Usage

```python
@bot.cron("0 9 * * 1")   # Every Monday at 09:00 UTC
async def weekly_report():
    await bot.rest.create_message(CHANNEL_ID, "Weekly report!")

@bot.cron("*/30 * * * *")  # Every 30 minutes
async def heartbeat():
    print("Still alive")
```

Jobs start automatically when the bot is ready and stop on shutdown.

## Cron syntax

```
┌─ minute (0-59)
│ ┌─ hour (0-23)
│ │ ┌─ day of month (1-31)
│ │ │ ┌─ month (1-12)
│ │ │ │ ┌─ day of week (0-6, Sun=0)
│ │ │ │ │
* * * * *
```

Common examples:

| Expression | Meaning |
|---|---|
| `0 9 * * *` | Every day at 09:00 |
| `0 9 * * 1` | Every Monday at 09:00 |
| `*/5 * * * *` | Every 5 minutes |
| `0 0 1 * *` | First day of every month |
