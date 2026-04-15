import asyncio
import hashlib
import os
import secrets
import subprocess
import sys
import tempfile
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Firebase init ──────────────────────────────────────────────────────────────
cred = credentials.Certificate(os.environ["FIREBASE_CREDENTIALS_JSON"])
firebase_admin.initialize_app(cred)
db = firestore.client()

_bots:    dict[str, dict] = {}   # token → {proc, code}  (in-memory only)
_sessions: dict[str, str] = {}   # session_token → username  (in-memory, short-lived)


# ── Firestore helpers ──────────────────────────────────────────────────────────

def _get_user(username: str) -> Optional[dict]:
    doc = db.collection("users").document(username).get()
    return doc.to_dict() if doc.exists else None

def _set_user(username: str, data: dict):
    db.collection("users").document(username).set(data)

def _get_bots() -> dict:
    doc = db.collection("state").document("bots").get()
    return doc.to_dict() or {} if doc.exists else {}

def _save_bots():
    db.collection("state").document("bots").set(
        {token: bot["code"] for token, bot in _bots.items()}
    )

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


# ── Bot process management ─────────────────────────────────────────────────────

def _launch(token: str, code: str) -> subprocess.Popen:
    code = code.replace('os.environ["NERIMITY_TOKEN"]', f'"{token}"')
    code = code.replace("os.environ['NERIMITY_TOKEN']", f'"{token}"')
    tmp = tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w")
    tmp.write(code)
    tmp.flush()
    tmp.close()
    return subprocess.Popen(
        [sys.executable, tmp.name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "NERIMITY_TOKEN": token, "NERIMITY_CHILD": "1"},
    )

async def _watchdog():
    while True:
        await asyncio.sleep(20)
        for token, bot in list(_bots.items()):
            if bot["proc"].poll() is not None:
                bot["proc"] = _launch(token, bot["code"])


# ── Auth helpers ───────────────────────────────────────────────────────────────

def _require_session(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.removeprefix("Bearer ").strip()
    username = _sessions.get(token)
    if not username:
        raise HTTPException(401, "Invalid or expired session")
    return username


# ── Startup ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    # reload bots from Firestore
    for token, code in _get_bots().items():
        _bots[token] = {"proc": _launch(token, code), "code": code}
    asyncio.create_task(_watchdog())


# ── Auth endpoints ─────────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    username: str
    password: str

@app.post("/auth/register")
async def register(req: AuthRequest):
    u = req.username.strip().lower()
    if len(u) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")
    if _get_user(u):
        raise HTTPException(409, "Username already taken")
    _set_user(u, {"pw_hash": _hash(req.password), "bot_token": ""})
    session = secrets.token_hex(32)
    _sessions[session] = u
    return {"session": session, "username": u, "bot_token": ""}

@app.post("/auth/login")
async def login(req: AuthRequest):
    u = req.username.strip().lower()
    user = _get_user(u)
    if not user or user["pw_hash"] != _hash(req.password):
        raise HTTPException(401, "Invalid username or password")
    session = secrets.token_hex(32)
    _sessions[session] = u
    return {"session": session, "username": u, "bot_token": user.get("bot_token", "")}

@app.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    _sessions.pop(token, None)
    return {"status": "logged out"}


# ── Bot endpoints ──────────────────────────────────────────────────────────────

class DeployRequest(BaseModel):
    code: str
    bot_token: Optional[str] = None

@app.post("/deploy")
async def deploy(req: DeployRequest, authorization: Optional[str] = Header(None)):
    username = _require_session(authorization)
    user = _get_user(username)
    token = (req.bot_token or user.get("bot_token", "")).strip()
    if not token:
        raise HTTPException(400, "No bot token saved to your account")
    if req.bot_token and req.bot_token != user.get("bot_token"):
        user["bot_token"] = req.bot_token.strip()
        _set_user(username, user)
    if token in _bots:
        p = _bots[token]["proc"]
        if p.poll() is None:
            p.terminate()
    _bots[token] = {"proc": _launch(token, req.code), "code": req.code}
    _save_bots()
    return {"status": "started"}

@app.post("/stop")
async def stop(authorization: Optional[str] = Header(None)):
    username = _require_session(authorization)
    token = (_get_user(username) or {}).get("bot_token", "")
    bot = _bots.pop(token, None)
    if bot and bot["proc"].poll() is None:
        bot["proc"].terminate()
    _save_bots()
    return {"status": "stopped"}

@app.get("/status")
async def status(authorization: Optional[str] = Header(None)):
    username = _require_session(authorization)
    token = (_get_user(username) or {}).get("bot_token", "")
    bot = _bots.get(token)
    return {"running": bool(bot and bot["proc"].poll() is None), "bot_token": token}

@app.get("/health")
async def health():
    return {"ok": True, "bots": len(_bots)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
