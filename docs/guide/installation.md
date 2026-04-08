# Installation

## Requirements

- Python 3.10+
- A Nerimity bot token

## Install

```bash
pip install nerimity-sdk
```

### Optional extras

```bash
# Redis cache / storage backend
pip install "nerimity-sdk[redis]"

# SQLite storage backend
pip install "nerimity-sdk[sqlite]"

# Cron scheduler
pip install "nerimity-sdk[cron]"

# Dev watch mode (auto-reload plugins on file save)
pip install "nerimity-sdk[watch]"

# Everything
pip install "nerimity-sdk[redis,sqlite,cron,watch]"
```

## Scaffold a project

```bash
nerimity create my-bot
cd my-bot
```

This creates:

```
my-bot/
├── bot.py              # Main bot file
├── plugins/
│   └── greeter.py      # Example plugin
├── .env.example        # Token template
├── .gitignore
└── README.md
```

Set your token:

```bash
cp .env.example .env
# Edit .env and set NERIMITY_TOKEN=your_token_here
```

Then run:

```bash
python bot.py
```
