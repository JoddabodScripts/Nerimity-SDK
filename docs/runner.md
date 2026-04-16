# Runner

The Bot Zombie runner is a FastAPI server that powers the bot builder. It handles authentication, bot deployment, and lifecycle management.

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves the bot builder UI |
| `GET` | `/health` | Health check -- returns `{"ok": true, "bots": N}` |
| `POST` | `/auth/register` | Create a new account |
| `POST` | `/auth/login` | Log in and get a session token |
| `POST` | `/auth/logout` | Invalidate the current session |
| `GET` | `/tokens` | List saved bot tokens |
| `POST` | `/tokens/add` | Save a new bot token |
| `POST` | `/tokens/remove` | Remove a saved bot token |
| `POST` | `/deploy` | Deploy bot code (requires auth) |
| `POST` | `/stop` | Stop a running bot |
| `GET` | `/logs` | Fetch recent logs for your bots |

---

## Architecture

```
Browser (builder.html)
    │
    ▼
FastAPI server (runner.py)
    │
    ├─► Firebase Firestore (user accounts, bot state)
    │
    └─► Node.js child processes (one per deployed bot)
```

- **Auth**: Username/password with PBKDF2-HMAC-SHA256 hashing (100k iterations). Session tokens stored in Firestore.
- **Deploy**: User code is written to a temp directory with a `package.json`, `npm install` runs, then `node bot.js` is spawned as a child process.
- **Watchdog**: A background task checks every 20 seconds for crashed bots and auto-restarts them.
- **Security**: Child processes get a minimal environment (only `PATH`, `HOME`, `NODE_ENV`, etc.) -- server secrets like `FIREBASE_CREDENTIALS_JSON` are never exposed.

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `FIREBASE_CREDENTIALS_JSON` | Yes | Firebase service account JSON (as a string) |
| `PORT` | No | Server port (default: `8080`) |
| `CORS_ORIGINS` | No | Comma-separated allowed origins (default: Fly.io app URL) |

---

## Deployment

### Fly.io

```bash
cd runner
fly deploy
```

The included `fly.toml` and `Dockerfile` handle everything. The Dockerfile installs Python 3.11 and Node.js 20.

### Render

A `render.yaml` is included at the repo root for one-click Render deployment.

### Railway

A `railpack.json` is included in `runner/` for Railway deployment.
