"""MIRA Local Agent - safe bridge for future PC actions.

Run this on Boss's Windows PC. It intentionally exposes only a small allowlist
and requires a per-request token. No arbitrary shell execution is provided.
"""
from __future__ import annotations

import os
import secrets
import subprocess
import time
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="MIRA Local Agent", version="1.0")
AGENT_TOKEN = os.getenv("MIRA_AGENT_TOKEN")
if not AGENT_TOKEN:
    AGENT_TOKEN = secrets.token_urlsafe(32)
    print("MIRA_AGENT_TOKEN (save this locally):", AGENT_TOKEN)

WORKSPACE = Path(os.getenv("MIRA_AGENT_WORKSPACE", str(Path.home() / "MIRA_Workspace"))).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)

ALLOWED_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
}

class AppRequest(BaseModel):
    app: str

class OpenPathRequest(BaseModel):
    path: str


def auth(token: str | None):
    if not token or not secrets.compare_digest(token, AGENT_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")


def safe_path(raw: str) -> Path:
    p = Path(raw).expanduser().resolve()
    if p != WORKSPACE and WORKSPACE not in p.parents:
        raise HTTPException(status_code=403, detail="Path outside MIRA workspace")
    return p

@app.get("/")
def home():
    return {"agent": "MIRA Local Agent", "status": "ONLINE", "workspace": str(WORKSPACE)}

@app.get("/health")
def health():
    return {"status": "ok", "agent": "MIRA Local Agent"}

@app.post("/open-app")
def open_app(req: AppRequest, x_mira_token: str | None = Header(default=None)):
    auth(x_mira_token)
    key = req.app.lower().strip()
    if key not in ALLOWED_APPS:
        raise HTTPException(status_code=403, detail="App is not allowlisted")
    subprocess.Popen([ALLOWED_APPS[key]], shell=False)
    return {"ok": True, "action": "open-app", "app": key}

@app.post("/open-path")
def open_path(req: OpenPathRequest, x_mira_token: str | None = Header(default=None)):
    auth(x_mira_token)
    p = safe_path(req.path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    os.startfile(str(p))
    return {"ok": True, "action": "open-path", "path": str(p)}

@app.get("/workspace")
def workspace(x_mira_token: str | None = Header(default=None)):
    auth(x_mira_token)
    files = [str(p.relative_to(WORKSPACE)) for p in WORKSPACE.rglob("*") if p.is_file()]
    return {"ok": True, "files": files[:500]}
