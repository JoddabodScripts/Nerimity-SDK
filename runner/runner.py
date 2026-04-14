"""
Hosted bot runner — receives generated bot code from the builder and runs it.
Deploy this to Fly.io (free tier) so anyone can host their bot without a server.
"""
import asyncio
import os
import subprocess
import sys
import tempfile
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# token → running subprocess
_procs: dict[str, subprocess.Popen] = {}


class DeployRequest(BaseModel):
    token: str
    code: str


class StatusResponse(BaseModel):
    running: bool
    token_hint: str  # first 8 chars only, never expose full token


@app.post("/deploy")
async def deploy(req: DeployRequest):
    token = req.token.strip()
    if not token:
        raise HTTPException(400, "token is required")

    # Stop existing process for this token if any
    _stop(token)

    # Write code to a temp file, injecting the token as env var
    tmp = tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w")
    # Replace any hardcoded token references with the env var
    code = req.code.replace('os.environ["NERIMITY_TOKEN"]', f'"{token}"')
    code = code.replace("os.environ['NERIMITY_TOKEN']", f'"{token}"')
    tmp.write(code)
    tmp.flush()
    tmp.close()

    proc = subprocess.Popen(
        [sys.executable, tmp.name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "NERIMITY_TOKEN": token, "NERIMITY_CHILD": "1"},
    )
    _procs[token] = proc
    return {"status": "started", "token_hint": token[:8] + "..."}


@app.post("/stop")
async def stop(req: DeployRequest):
    token = req.token.strip()
    _stop(token)
    return {"status": "stopped"}


@app.get("/status/{token_hint}")
async def status(token_hint: str):
    for token, proc in _procs.items():
        if token.startswith(token_hint):
            alive = proc.poll() is None
            return {"running": alive, "token_hint": token[:8] + "..."}
    return {"running": False, "token_hint": token_hint}


def _stop(token: str):
    proc = _procs.pop(token, None)
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
