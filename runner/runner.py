import asyncio
import atexit
import hashlib
import json
import os
import re
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

# ── Input-validation constants ──────────────────────────────────────────
MAX_CODE_LENGTH = 50_000  # 50 KB

# Node.js built-in modules that user code must never load.
BLOCKED_MODULES: frozenset[str] = frozenset({
    "child_process", "fs", "fs/promises",
    "net", "dgram", "tls",
    "cluster", "worker_threads",
    "vm", "v8",
    "os",
    "inspector", "repl", "readline",
    "trace_events", "perf_hooks", "async_hooks",
})
# Also block the node:-prefixed forms (e.g. "node:fs").
_BLOCKED_ALL = BLOCKED_MODULES | frozenset(f"node:{m}" for m in BLOCKED_MODULES)

_RE_REQUIRE = re.compile(r"""require\s*\(\s*(['"`])(.*?)\1\s*\)""")
_RE_IMPORT_FROM = re.compile(r"""import\s+.*?\s+from\s+(['"`])(.*?)\1""")
_RE_IMPORT_DYNAMIC = re.compile(r"""import\s*\(\s*(['"`])(.*?)\1\s*\)""")
_RE_IMPORT_BARE = re.compile(r"""import\s+(['"`])(.*?)\1""")

DANGEROUS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bprocess\s*\.\s*binding\b"),  "process.binding is blocked"),
    (re.compile(r"\bprocess\s*\.\s*dlopen\b"),   "process.dlopen is blocked"),
    (re.compile(r"\beval\s*\("),                  "eval() is blocked"),
    (re.compile(r"\bnew\s+Function\s*\("),        "new Function() is blocked"),
    (re.compile(r"\bFunction\s*\("),              "Function() constructor is blocked"),
    (re.compile(r"\b__dirname\b"),                "__dirname is blocked"),
    (re.compile(r"\b__filename\b"),               "__filename is blocked"),
]


def _extract_modules(code: str) -> set[str]:
    """Return every module name referenced by require() or import."""
    modules: set[str] = set()
    for m in _RE_REQUIRE.finditer(code):
        modules.add(m.group(2))
    for m in _RE_IMPORT_FROM.finditer(code):
        modules.add(m.group(2))
    for m in _RE_IMPORT_DYNAMIC.finditer(code):
        modules.add(m.group(2))
    for m in _RE_IMPORT_BARE.finditer(code):
        modules.add(m.group(2))
    return modules


def _check_process_env(code: str) -> str | None:
    """Block process.env access except for process.env.NERIMITY_TOKEN."""
    sanitized = re.sub(r"\bprocess\.env\.NERIMITY_TOKEN\b", "", code)
    if re.search(r"\bprocess\s*\.\s*env\b", sanitized):
        return "access to process.env is blocked (only process.env.NERIMITY_TOKEN is allowed)"
    return None


def validate_code(code: str) -> tuple[bool, str]:
    """
    Validate user-provided bot code before deployment.

    Returns ``(True, "")`` when the code passes all checks, or
    ``(False, reason)`` when a violation is detected.
    """
    if not code or not code.strip():
        return False, "Code must not be empty"

    if len(code) > MAX_CODE_LENGTH:
        return False, f"Code exceeds the maximum allowed length of {MAX_CODE_LENGTH:,} characters"

    # Blocked module imports / requires
    blocked = _extract_modules(code) & _BLOCKED_ALL
    if blocked:
        return False, f"Blocked module(s): {', '.join(sorted(blocked))}"

    # Dangerous runtime patterns
    for pattern, message in DANGEROUS_PATTERNS:
        if pattern.search(code):
            return False, message

    # process.env leak (allow only NERIMITY_TOKEN)
    env_err = _check_process_env(code)
    if env_err:
        return False, env_err

    return True, ""


def _sanitize_token_for_js(token: str) -> str:
    """Escape a bot token so it can be safely embedded in a JS string literal."""
    return (
        token
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


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

    safe_token = _sanitize_token_for_js(token)
    with open(bot_path, "w") as f:
        f.write(code.replace("process.env.NERIMITY_TOKEN", f'"{safe_token}"'))
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

    # ── Validate user-provided code before deployment ──
    ok, reason = validate_code(req.code)
    if not ok:
        raise HTTPException(400, f"Code validation failed: {reason}")

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
