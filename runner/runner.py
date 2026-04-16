import asyncio
import atexit
import hashlib
import json
import os
import secrets
import subprocess
import sys
import tempfile
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore

_MAX_LOG_BYTES = 500_000  # truncate bot logs beyond 500 KB

_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ORIGINS", "https://runner-cold-grass-3880.fly.dev"
).split(",")

_cred_data = json.loads(os.environ["FIREBASE_CREDENTIALS_JSON"])
cred = credentials.Certificate(_cred_data)
firebase_admin.initialize_app(cred)
db = firestore.client()

_bots:     dict[str, dict] = {}
_sessions: dict[str, str]  = {}

def _get_user(u): doc = db.collection("users").document(u).get(); return doc.to_dict() if doc.exists else None
def _set_user(u, d): db.collection("users").document(u).set(d)
def _hash(pw, salt=None):
    """Hash a password with PBKDF2-HMAC-SHA256 (100k iterations)."""
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 100_000)
    return salt.hex() + ":" + dk.hex()

def _verify(pw, stored):
    """Verify a password against a stored PBKDF2 hash."""
    if ":" not in stored:
        # Legacy unsalted SHA-256 hash -- verify and signal upgrade needed
        return stored == hashlib.sha256(pw.encode()).hexdigest(), True
    salt_hex, _ = stored.split(":", 1)
    return _hash(pw, bytes.fromhex(salt_hex)) == stored, False
def _save_bots(): db.collection("state").document("bots").set({t: b["code"] for t, b in _bots.items()})

def _require_session(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    tok = authorization.removeprefix("Bearer ").strip()
    u = _sessions.get(tok)
    if not u:
        doc = db.collection("sessions").document(tok).get()
        if not doc.exists: raise HTTPException(401, "Invalid or expired session")
        u = doc.to_dict()["username"]; _sessions[tok] = u
    return u

# Env vars that are safe to pass to child bot processes.
_SAFE_ENV_KEYS = {"PATH", "HOME", "USER", "LANG", "NODE_PATH", "NODE_ENV", "PORT"}

def _safe_child_env(token: str) -> dict:
    """Build a minimal environment for child bot processes.

    Excludes server secrets like FIREBASE_CREDENTIALS_JSON.
    """
    env = {k: v for k, v in os.environ.items() if k in _SAFE_ENV_KEYS}
    env["NERIMITY_TOKEN"] = token
    env["NERIMITY_CHILD"] = "1"
    return env

def _launch(token: str, code: str):
    # Write bot.js to a temp dir with package.json
    tmpdir = tempfile.mkdtemp()
    bot_path = os.path.join(tmpdir, "bot.js")
    pkg_path = os.path.join(tmpdir, "package.json")
    log_path = os.path.join(tmpdir, "bot.log")

    with open(bot_path, "w") as f:
        f.write(code.replace("process.env.NERIMITY_TOKEN", f'"{token}"'))
    with open(pkg_path, "w") as f:
        json.dump({"name": "bot", "version": "1.0.0", "dependencies": {"@nerimity/nerimity.js": "latest"}}, f)

    # npm install then node bot.js
    subprocess.run(["npm", "install", "--prefer-offline"], cwd=tmpdir, capture_output=True)
    log = open(log_path, "w")
    proc = subprocess.Popen(
        ["node", bot_path],
        stdout=log, stderr=log,
        env=_safe_child_env(token),
        cwd=tmpdir,
    )
    return proc, log_path

def _truncate_logs():
    """Trim bot log files that exceed _MAX_LOG_BYTES."""
    for bot in _bots.values():
        logpath = bot.get("log")
        if not logpath:
            continue
        try:
            size = os.path.getsize(logpath)
            if size > _MAX_LOG_BYTES:
                with open(logpath, "r+") as f:
                    f.seek(size - _MAX_LOG_BYTES)
                    tail = f.read()
                    f.seek(0); f.write(tail); f.truncate()
        except OSError:
            pass

async def _watchdog():
    while True:
        await asyncio.sleep(20)
        for token, bot in list(_bots.items()):
            if bot["proc"].poll() is not None:
                proc, logpath = _launch(token, bot["code"])
                bot["proc"] = proc; bot["log"] = logpath
        _truncate_logs()

def _shutdown_bots():
    """Terminate all child bot processes on server shutdown."""
    for token, bot in list(_bots.items()):
        proc = bot.get("proc")
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

atexit.register(_shutdown_bots)

@asynccontextmanager
async def lifespan(application: FastAPI):
    # Startup: restore bots and start watchdog
    doc = db.collection("state").document("bots").get()
    if doc.exists:
        for token, code in (doc.to_dict() or {}).items():
            proc, logpath = _launch(token, code)
            _bots[token] = {"proc": proc, "code": code, "log": logpath}
    asyncio.create_task(_watchdog())
    yield
    # Shutdown: terminate all bots
    _shutdown_bots()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

class AuthRequest(BaseModel):
    username: str
    password: str

@app.post("/auth/register")
async def register(req: AuthRequest):
    u = req.username.strip().lower()
    if len(u) < 3: raise HTTPException(400, "Username too short")
    if len(req.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if _get_user(u): raise HTTPException(409, "Username taken")
    _set_user(u, {"pw_hash": _hash(req.password), "tokens": []})
    session = secrets.token_hex(32); _sessions[session] = u
    db.collection("sessions").document(session).set({"username": u})
    return {"session": session, "username": u, "tokens": []}

@app.post("/auth/login")
async def login(req: AuthRequest):
    u = req.username.strip().lower()
    user = _get_user(u)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    ok, is_legacy = _verify(req.password, user["pw_hash"])
    if not ok:
        raise HTTPException(401, "Invalid credentials")
    # Transparently upgrade legacy SHA-256 hashes to PBKDF2
    if is_legacy:
        user["pw_hash"] = _hash(req.password)
        _set_user(u, user)
    session = secrets.token_hex(32); _sessions[session] = u
    db.collection("sessions").document(session).set({"username": u})
    return {"session": session, "username": u, "tokens": user.get("tokens", [])}

@app.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    tok = (authorization or "").removeprefix("Bearer ").strip()
    _sessions.pop(tok, None); db.collection("sessions").document(tok).delete()
    return {"status": "logged out"}

class TokenRequest(BaseModel):
    bot_token: str
    name: str = ""

@app.post("/tokens/add")
async def add_token(req: TokenRequest, authorization: Optional[str] = Header(None)):
    u = _require_session(authorization); user = _get_user(u)
    tokens = user.get("tokens", [])
    if not any(t["token"] == req.bot_token for t in tokens):
        tokens.append({"token": req.bot_token.strip(), "name": req.name or req.bot_token[:8] + "..."})
        user["tokens"] = tokens; _set_user(u, user)
    return {"tokens": [{"token_hint": t["token"][:8]+"...", "name": t.get("name",""), "running": t["token"] in _bots and _bots[t["token"]]["proc"].poll() is None} for t in tokens]}

@app.post("/tokens/remove")
async def remove_token(req: TokenRequest, authorization: Optional[str] = Header(None)):
    u = _require_session(authorization); user = _get_user(u)
    tokens = [t for t in user.get("tokens", []) if t["token"] != req.bot_token]
    user["tokens"] = tokens; _set_user(u, user)
    bot = _bots.pop(req.bot_token, None)
    if bot and bot["proc"].poll() is None: bot["proc"].terminate()
    _save_bots(); return {"tokens": tokens}

@app.get("/tokens")
async def list_tokens(authorization: Optional[str] = Header(None)):
    u = _require_session(authorization); user = _get_user(u)
    return {"tokens": [{"token_hint": t["token"][:8]+"...", "name": t.get("name",""), "running": t["token"] in _bots and _bots[t["token"]]["proc"].poll() is None} for t in user.get("tokens", [])]}

class DeployRequest(BaseModel):
    code: str
    bot_token: str

@app.post("/deploy")
async def deploy(req: DeployRequest, authorization: Optional[str] = Header(None)):
    u = _require_session(authorization); user = _get_user(u)
    token = req.bot_token.strip()
    if not token: raise HTTPException(400, "bot_token required")
    tokens = user.get("tokens", [])
    if not any(t["token"] == token for t in tokens):
        tokens.append({"token": token, "name": token[:8]+"..."}); user["tokens"] = tokens; _set_user(u, user)
    if token in _bots:
        p = _bots[token]["proc"]
        if p.poll() is None: p.terminate()
    proc, logpath = _launch(token, req.code)
    _bots[token] = {"proc": proc, "code": req.code, "log": logpath}
    _save_bots()
    return {"status": "started", "token_hint": token[:8]+"..."}

class StopRequest(BaseModel):
    bot_token: str

@app.post("/stop")
async def stop(req: StopRequest, authorization: Optional[str] = Header(None)):
    u = _require_session(authorization); user = _get_user(u)
    token = req.bot_token.strip()
    if not any(t["token"] == token for t in user.get("tokens", [])): raise HTTPException(403, "Not your token")
    bot = _bots.pop(token, None)
    if bot and bot["proc"].poll() is None: bot["proc"].terminate()
    _save_bots(); return {"status": "stopped"}

@app.get("/logs")
async def get_logs(authorization: Optional[str] = Header(None)):
    u = _require_session(authorization); user = _get_user(u)
    result = {}
    for t in user.get("tokens", []):
        bot = _bots.get(t["token"])
        if bot and "log" in bot:
            try:
                with open(bot["log"]) as f: result[t.get("name", t["token"][:8])] = f.read()[-3000:]
            except: result[t.get("name", t["token"][:8])] = "(no logs)"
    return result

@app.get("/health")
async def health(): return {"ok": True, "bots": len(_bots)}

@app.get("/", response_class=HTMLResponse)
async def index():
    import pathlib
    p = pathlib.Path(__file__).parent / "builder.html"
    return HTMLResponse(p.read_text())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
