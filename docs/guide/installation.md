# Installation

## Requirements

- Python 3.10 or newer
- A Nerimity bot token

---

## Step 1 — Install Python (Windows)

If you haven't installed Python yet:

1. Go to [python.org/downloads](https://www.python.org/downloads/) and download the latest version
2. Run the installer
3. ⚠️ **Check "Add Python to PATH"** before clicking Install — this is important!
4. Open **Command Prompt** (`Win + R` → type `cmd` → Enter)
5. Run `python --version` — if you see a version number, you're all set ✅

---

## Step 2 — Get a token

Your token is what lets your bot log in to Nerimity.

1. Go to [nerimity.com/app/settings/developer/applications](https://nerimity.com/app/settings/developer/applications)
2. Click **New Application** and give it a name
3. Go to the **Bot** tab → click **Add Bot**
4. Copy the token — **keep it secret, never share it or commit it to GitHub**

---

## Step 3 — Install the SDK

Open **Command Prompt** and run:

```
pip install nerimity-sdk
```

### Optional extras

Install only what you need:

```
pip install "nerimity-sdk[redis]"    # Redis storage backend
pip install "nerimity-sdk[sqlite]"   # SQLite storage backend
pip install "nerimity-sdk[cron]"     # Scheduled tasks
pip install "nerimity-sdk[watch]"    # Auto-reload on file save
pip install "nerimity-sdk[redis,sqlite,cron,watch]"   # Everything
```

---

## Step 4 — Create your project

```
nerimity create my-bot
cd my-bot
```

This creates a ready-to-go folder:

```
my-bot/
├── bot.py              # Your main bot file
├── plugins/
│   └── greeter.py      # An example plugin
├── .env.example        # Token template
├── .gitignore
└── README.md
```

Now set your token. In Command Prompt:

```
copy .env.example .env
```

Open `.env` in Notepad by running this in Command Prompt (`.env` files are hidden in File Explorer, so use this instead):

```
notepad .env
```

Replace the placeholder with your token:

```
NERIMITY_TOKEN=paste_your_token_here
```

Then run your bot:

```
python bot.py
```

You should see a "Logged in" message in the terminal. Your bot is online! 🎉

---

## Linux

```bash
pip install nerimity-sdk

nerimity create my-bot
cd my-bot
cp .env.example .env   # then edit .env and paste your token
python bot.py
```
