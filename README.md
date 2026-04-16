# Bot Zombie

A no-code bot creator for [Nerimity](https://nerimity.com). Build and deploy bots using a drag-and-drop node editor -- no coding required.

---

## What is Bot Zombie?

Bot Zombie lets you create Nerimity bots through a visual builder. Drag nodes onto a canvas, wire them together, and deploy -- your bot goes live instantly.

### Features

| Feature | Description |
|---|---|
| Visual node editor | Drag-and-drop canvas with wirable nodes |
| Ready-made templates | Start from pre-built bot templates |
| Live preview | Test your bot's responses before deploying |
| One-click deploy | Deploy directly from the builder |
| Bot dashboard | Manage all your bots, view logs, start/stop |
| Embed editor | Build rich embeds visually |
| Custom code | Drop into code view for full control |
| Account system | Register/login to save your bots |
| Auto-restart | Bots restart automatically if they crash |
| Input validation | Server-side code validation blocks dangerous patterns |

---

## Getting started

1. Go to [nerimity.com/app/settings/developer/applications](https://nerimity.com/app/settings/developer/applications)
2. Create a new app, add a Bot, and copy the token
3. Open the Bot Zombie builder, paste your token, and start building

---

## Self-hosting

Bot Zombie runs as a FastAPI server with Node.js for bot execution.

### Requirements

- Python 3.11+
- Node.js 20+
- A Firebase project (Firestore for storage)

### Setup

```bash
cd runner
pip install -r requirements.txt
```

Set the required environment variable:

```bash
export FIREBASE_CREDENTIALS_JSON='{ ... your Firebase service account JSON ... }'
```

### Run

```bash
python runner.py
```

The server starts on `http://localhost:8080`. Open it in your browser to access the builder.

### Deploy to Fly.io

The repo includes a `fly.toml` and `Dockerfile` ready for Fly.io deployment:

```bash
cd runner
fly deploy
```

### Deploy to Render

A `render.yaml` is included for Render deployment.

---

## Project structure

```
runner/
  runner.py        # FastAPI server -- auth, deploy, bot lifecycle
  builder.html     # Visual bot builder (served as the index page)
  Dockerfile       # Container config for deployment
  fly.toml         # Fly.io config
  requirements.txt # Python dependencies
docs/              # Documentation site (built with MkDocs)
mkdocs.yml         # MkDocs configuration
```

---

## Documentation

The full documentation site is built with MkDocs and hosted on ReadTheDocs. The landing page is the interactive bot builder itself.

---

Built by [@Kansane:TETO on Nerimity](https://nerimity.com/app/profile/1750075711936438273) | [JoddabodScripts on GitHub](https://github.com/JoddabodScripts)
