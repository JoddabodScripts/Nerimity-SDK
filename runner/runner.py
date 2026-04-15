import asyncio
import hashlib
import json
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

_cred_data = json.loads(os.environ["FIREBASE_CREDENTIALS_JSON"])
cred = credentials.Certificate(_cred_data)
firebase_admin.initialize_app(cred)
db = firestore.client()

_bots:     dict[str, dict] = {}   # token → {proc, code}
_sessions: dict[str, str]  = {}   # session → username


# ── Firestore ──────────────────────────────────────────────────────────────────

def _get_user(u: str) -> Optional[dict]:
    doc = db.collection("users").document(u).get()
    return doc.to_dict() if doc.exists else None

def _set_user(u: str, data: dict):
    db.collection("users").document(u).set(data)

def _save_bots():
    db.collection("state").document("bots").set(
        {t: b["code"] for t, b in _bots.items()}
    )

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


# ── Process management ─────────────────────────────────────────────────────────

def _launch(token: str, code: str) -> subprocess.Popen:
    code = code.replace('os.environ["NERIMITY_TOKEN"]', f'"{token}"')
    code = code.replace("os.environ['NERIMITY_TOKEN']", f'"{token}"')
    tmp = tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w")
    tmp.write(code); tmp.flush(); tmp.close()
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

@app.on_event("startup")
async def startup():
    doc = db.collection("state").document("bots").get()
    if doc.exists:
        for token, code in (doc.to_dict() or {}).items():
            _bots[token] = {"proc": _launch(token, code), "code": code}
    asyncio.create_task(_watchdog())


# ── Auth ───────────────────────────────────────────────────────────────────────

def _require_session(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    tok = authorization.removeprefix("Bearer ").strip()
    u = _sessions.get(tok)
    if not u:
        raise HTTPException(401, "Invalid or expired session")
    return u

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
    _set_user(u, {"pw_hash": _hash(req.password), "tokens": []})
    session = secrets.token_hex(32)
    _sessions[session] = u
    return {"session": session, "username": u, "tokens": []}

@app.post("/auth/login")
async def login(req: AuthRequest):
    u = req.username.strip().lower()
    user = _get_user(u)
    if not user or user["pw_hash"] != _hash(req.password):
        raise HTTPException(401, "Invalid username or password")
    session = secrets.token_hex(32)
    _sessions[session] = u
    return {"session": session, "username": u, "tokens": user.get("tokens", [])}

@app.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    _sessions.pop((authorization or "").removeprefix("Bearer ").strip(), None)
    return {"status": "logged out"}


# ── Token management ───────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    bot_token: str
    name: str = ""

@app.post("/tokens/add")
async def add_token(req: TokenRequest, authorization: Optional[str] = Header(None)):
    u = _require_session(authorization)
    user = _get_user(u)
    tokens = user.get("tokens", [])
    if not any(t["token"] == req.bot_token for t in tokens):
        tokens.append({"token": req.bot_token.strip(), "name": req.name or req.bot_token[:8] + "..."})
        user["tokens"] = tokens
        _set_user(u, user)
    return {"tokens": [{k: v for k, v in t.items() if k != "token"} | {"token_hint": t["token"][:8] + "..."} for t in tokens]}

@app.post("/tokens/remove")
async def remove_token(req: TokenRequest, authorization: Optional[str] = Header(None)):
    u = _require_session(authorization)
    user = _get_user(u)
    tokens = [t for t in user.get("tokens", []) if t["token"] != req.bot_token]
    user["tokens"] = tokens
    _set_user(u, user)
    bot = _bots.pop(req.bot_token, None)
    if bot and bot["proc"].poll() is None:
        bot["proc"].terminate()
    _save_bots()
    return {"tokens": tokens}

@app.get("/tokens")
async def list_tokens(authorization: Optional[str] = Header(None)):
    u = _require_session(authorization)
    user = _get_user(u)
    return {"tokens": [
        {"token": t["token"], "token_hint": t["token"][:8] + "...", "name": t.get("name", ""), "running": t["token"] in _bots and _bots[t["token"]]["proc"].poll() is None}
        for t in user.get("tokens", [])
    ]}


# ── Deploy / stop ──────────────────────────────────────────────────────────────

class DeployRequest(BaseModel):
    code: str
    bot_token: str  # must specify which token to deploy

@app.post("/deploy")
async def deploy(req: DeployRequest, authorization: Optional[str] = Header(None)):
    u = _require_session(authorization)
    user = _get_user(u)
    token = req.bot_token.strip()
    if not token:
        raise HTTPException(400, "bot_token required")
    tokens = user.get("tokens", [])
    if not any(t["token"] == token for t in tokens):
        tokens.append({"token": token, "name": token[:8] + "..."})
        user["tokens"] = tokens
        _set_user(u, user)
    if token in _bots:
        p = _bots[token]["proc"]
        if p.poll() is None:
            p.terminate()
    _bots[token] = {"proc": _launch(token, req.code), "code": req.code}
    _save_bots()
    return {"status": "started", "token_hint": token[:8] + "..."}

class StopRequest(BaseModel):
    bot_token: str

@app.post("/stop")
async def stop(req: StopRequest, authorization: Optional[str] = Header(None)):
    u = _require_session(authorization)
    user = _get_user(u)
    token = req.bot_token.strip()
    if not any(t["token"] == token for t in user.get("tokens", [])):
        raise HTTPException(403, "Token not in your account")
    bot = _bots.pop(token, None)
    if bot and bot["proc"].poll() is None:
        bot["proc"].terminate()
    _save_bots()
    return {"status": "stopped"}

@app.get("/status")
async def status(authorization: Optional[str] = Header(None)):
    u = _require_session(authorization)
    user = _get_user(u)
    return {"tokens": [
        {"token_hint": t["token"][:8] + "...", "name": t.get("name", ""), "running": t["token"] in _bots and _bots[t["token"]]["proc"].poll() is None}
        for t in user.get("tokens", [])
    ]}

@app.get("/health")
async def health():
    return {"ok": True, "bots": len(_bots)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
