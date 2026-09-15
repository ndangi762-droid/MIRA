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

_QUEUE: deque[dict[str, Any]] = deque(maxlen=50)
_LAST_RESULT: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
_TOKEN = os.getenv("MIRA_PC_TOKEN", "mira-local")


class PCCommandRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    device: str = Field(default="windows", min_length=1, max_length=50)


def parse_message(message: str) -> dict[str, Any] | None:
    text = " ".join(message.lower().strip().split())
    open_words = ("open", "khol", "kholo", "chalao", "start", "launch")

    apps = {
        "chrome": "chrome",
        "google chrome": "chrome",
        "notepad": "notepad",
        "notes": "notepad",
        "calculator": "calculator",
        "calc": "calculator",
        "paint": "paint",
        "explorer": "explorer",
        "file explorer": "explorer",
        "task manager": "task_manager",
    }
    if any(w in text for w in open_words):
        for alias, target in sorted(apps.items(), key=lambda x: -len(x[0])):
            if alias in text:
                return {"action": "open_app", "target": target}

    sites = {
        "youtube": "https://www.youtube.com/",
        "gmail": "https://mail.google.com/",
        "google": "https://www.google.com/",
        "github": "https://github.com/",
    }
    if any(w in text for w in open_words):
        for alias, url in sites.items():
            if alias in text:
                return {"action": "open_url", "target": url}

    prefixes = ("search ", "google par ", "google me ", "search karo ", "search for ")
    for prefix in prefixes:
        if text.startswith(prefix):
            query = text[len(prefix):].strip()
            if query:
                return {"action": "search_web", "target": query}

    if text.startswith(("type ", "likho ", "type karo ")):
        for prefix in ("type karo ", "type ", "likho "):
            if text.startswith(prefix):
                value = message.strip()[len(prefix):].strip()
                if value:
                    return {"action": "type_text", "text": value}

    hotkeys = {
        "copy": ["ctrl", "c"],
        "paste": ["ctrl", "v"],
        "select all": ["ctrl", "a"],
        "save": ["ctrl", "s"],
        "undo": ["ctrl", "z"],
        "redo": ["ctrl", "y"],
        "close window": ["alt", "f4"],
    }
    for phrase, keys in hotkeys.items():
        if phrase in text:
            return {"action": "hotkey", "keys": keys}

    return None


@router.post("/api/pc/command")
async def queue_pc_command(req: PCCommandRequest):
    command = parse_message(req.message)
    if not command:
        raise HTTPException(status_code=400, detail="I could not map that request to a safe PC action yet.")
    command_id = uuid.uuid4().hex
    item = {"id": command_id, "device": req.device, "created_at": time.time(), **command}
    with _LOCK:
        _QUEUE.append(item)
        _LAST_RESULT[command_id] = {"status": "queued", "message": "Command queued."}
    return {"assistant": "MIRA", "status": "queued", "command_id": command_id, "action": command["action"]}


@router.get("/api/pc/poll")
async def poll_pc_command(token: str, device: str = "windows"):
    if token != _TOKEN:
        raise HTTPException(status_code=401, detail="Invalid PC agent token")
    with _LOCK:
        for item in list(_QUEUE):
            if item.get("device") == device:
                _QUEUE.remove(item)
                return {"command": item}
    return {"command": None}


@router.post("/api/pc/ack")
async def ack_pc_command(token: str, command_id: str, ok: bool, message: str = ""):
    if token != _TOKEN:
        raise HTTPException(status_code=401, detail="Invalid PC agent token")
    with _LOCK:
        _LAST_RESULT[command_id] = {"status": "done" if ok else "error", "message": message[:1000]}
    return {"status": "ok"}


@router.get("/api/pc/result/{command_id}")
async def pc_result(command_id: str):
    with _LOCK:
        result = _LAST_RESULT.get(command_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Command not found")
    return {"command_id": command_id, **result}


@router.get("/api/pc/status")
async def pc_status():
    with _LOCK:
        return {"assistant": "MIRA", "queued": len(_QUEUE), "agent": "polling" if _QUEUE else "ready"}
