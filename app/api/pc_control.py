from __future__ import annotations

import os
import threading
import time
import uuid
from collections import deque
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()
_QUEUE: deque[dict[str, Any]] = deque(maxlen=100)
_LAST_RESULT: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
_TOKEN = os.getenv("MIRA_PC_TOKEN", "mira-local")


class PCCommandRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    device: str = Field(default="windows", min_length=1, max_length=50)


def parse_message(message: str) -> dict[str, Any] | None:
    original = message.strip()
    text = " ".join(original.lower().split())
    open_words = ("open", "khol", "kholo", "chalao", "start", "launch")
    apps = {
        "google chrome": "chrome", "chrome": "chrome", "notepad": "notepad",
        "notes": "notepad", "calculator": "calculator", "calc": "calculator",
        "paint": "paint", "file explorer": "explorer", "explorer": "explorer",
        "task manager": "task_manager",
    }
    if any(w in text for w in open_words):
        for alias, target in sorted(apps.items(), key=lambda x: -len(x[0])):
            if alias in text:
                return {"action": "open_app", "target": target}
    sites = {"youtube": "https://www.youtube.com/", "gmail": "https://mail.google.com/", "google": "https://www.google.com/", "github": "https://github.com/"}
    if any(w in text for w in open_words):
        for alias, url in sites.items():
            if alias in text:
                return {"action": "open_url", "target": url}
    prefixes = ("search karo ", "search for ", "search ", "google par ", "google me ")
    for prefix in prefixes:
        if text.startswith(prefix):
            query = original[len(prefix):].strip()
            if query:
                return {"action": "search_web", "target": query[:1000]}
    for prefix in ("type karo ", "type ", "likho "):
        if text.startswith(prefix):
            value = original[len(prefix):].strip()
            if value:
                return {"action": "type_text", "text": value[:5000]}
    hotkeys = {
        "copy": ["ctrl", "c"], "paste": ["ctrl", "v"], "select all": ["ctrl", "a"],
        "save": ["ctrl", "s"], "undo": ["ctrl", "z"], "redo": ["ctrl", "y"],
        "close window": ["alt", "f4"], "switch window": ["alt", "tab"],
    }
    for phrase, keys in hotkeys.items():
        if phrase in text:
            return {"action": "hotkey", "keys": keys}
    if text.startswith(("click ", "click karo ")):
        parts = text.replace("click karo ", "click ", 1).split()
        if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
            return {"action": "click", "x": int(parts[1]), "y": int(parts[2])}
    return None


@router.post("/api/pc2/command")
async def queue_pc_command(req: PCCommandRequest):
    command = parse_message(req.message)
    if not command:
        raise HTTPException(status_code=400, detail="PC action is not mapped to a safe command yet.")
    command_id = uuid.uuid4().hex
    item = {"id": command_id, "device": req.device, "created_at": time.time(), **command}
    with _LOCK:
        _QUEUE.append(item)
        _LAST_RESULT[command_id] = {"status": "queued", "message": "Command queued."}
    return {"assistant": "MIRA", "status": "queued", "command_id": command_id, "action": command["action"]}


@router.get("/api/pc2/poll")
async def poll_pc_command(token: str, device: str = "windows"):
    if token != _TOKEN:
        raise HTTPException(status_code=401, detail="Invalid PC agent token")
    with _LOCK:
        for item in list(_QUEUE):
            if item.get("device") == device:
                _QUEUE.remove(item)
                return {"command": item}
    return {"command": None}


@router.post("/api/pc2/ack")
async def ack_pc_command(token: str, command_id: str, ok: bool, message: str = ""):
    if token != _TOKEN:
        raise HTTPException(status_code=401, detail="Invalid PC agent token")
    with _LOCK:
        _LAST_RESULT[command_id] = {"status": "done" if ok else "error", "message": message[:1000]}
    return {"status": "ok"}


@router.get("/api/pc2/result/{command_id}")
async def pc_result(command_id: str):
    with _LOCK:
        result = _LAST_RESULT.get(command_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Command not found")
    return {"command_id": command_id, **result}


@router.get("/api/pc2/status")
async def pc_status():
    with _LOCK:
        return {"assistant": "MIRA", "queued": len(_QUEUE), "agent": "polling" if _QUEUE else "ready"}
