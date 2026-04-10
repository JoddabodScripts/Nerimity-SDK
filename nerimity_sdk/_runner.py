"""Subprocess self-relaunch runner.

When Bot.run() is called from a normal `python bot.py` invocation, this module
re-executes the same script inside a child process and:
  - Restarts it automatically if it crashes
  - Restarts it when any .py file in the working directory is modified or created

The parent process is purely a watchdog — all bot logic runs in the child.
Set the env var NERIMITY_CHILD=1 to skip the wrapper (the child sets this itself).
"""
from __future__ import annotations
import os
import subprocess
import sys
import time


_WATCH_INTERVAL = 1.5  # seconds between file-change polls


def _snapshot(directory: str) -> dict[str, float]:
    snap: dict[str, float] = {}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs
                   if not d.startswith(".") and d not in ("__pycache__", "venv", ".venv", "site")]
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                try:
                    snap[path] = os.path.getmtime(path)
                except OSError:
                    pass
    return snap


def launch(script: str) -> None:
    """Run *script* in a child process, restarting on crash or file change."""
    directory = os.path.dirname(os.path.abspath(script))
    env = os.environ.copy()
    env["NERIMITY_CHILD"] = "1"
    cmd = [sys.executable] + sys.argv  # preserve any args the user passed

    while True:
        snapshot = _snapshot(directory)
        proc = subprocess.Popen(cmd, env=env)
        restart_reason: str | None = None

        try:
            while proc.poll() is None:
                time.sleep(_WATCH_INTERVAL)
                current = _snapshot(directory)
                changed = [p for p, m in current.items()
                           if snapshot.get(p) != m or p not in snapshot]
                if changed:
                    rel = os.path.relpath(changed[0], directory)
                    restart_reason = f"{rel} changed"
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    break
                snapshot = current
        except KeyboardInterrupt:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            return

        if restart_reason:
            print(f"\n[nerimity] {restart_reason} — restarting...\n", flush=True)
        elif proc.returncode not in (0, -2, 130):  # 130 = 128+SIGINT, -2 = SIGINT on Unix
            print(f"\n[nerimity] Bot exited with code {proc.returncode} — restarting in 2s...\n",
                  flush=True)
            time.sleep(2)
        else:
            return
