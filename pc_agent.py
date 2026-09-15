"""MIRA Windows PC bridge.

Run this ON THE USER'S WINDOWS PC. It listens only on localhost:8765 and
exposes a small allowlisted set of computer actions to the MIRA web UI.
No arbitrary shell commands are accepted.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote_plus

HOST = "127.0.0.1"
PORT = 8765
TOKEN = os.getenv("MIRA_PC_TOKEN", "mira-local")
ALLOWED_ORIGIN = "https://mira-premium.onrender.com"

APP_COMMANDS = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "explorer": ["explorer.exe"],
    "cmd": ["cmd.exe"],
}


def open_app(name: str):
    name = name.lower().strip()
    command = APP_COMMANDS.get(name)
    if not command:
        return {"ok": False, "message": f"App '{name}' is not allowlisted."}
    subprocess.Popen(command, shell=False)
    return {"ok": True, "message": f"{name.title()} opened."}


def open_website(target: str):
    target = target.strip()
    sites = {
        "google": "https://www.google.com/",
        "gmail": "https://mail.google.com/",
        "youtube": "https://www.youtube.com/",
        "github": "https://github.com/",
    }
    url = sites.get(target.lower())
    if not url:
        return {"ok": False, "message": "Website is not allowlisted."}
    webbrowser.open(url, new=2)
    return {"ok": True, "message": f"{target.title()} opened."}


def search_web(query: str):
    query = query.strip()
    if not query:
        return {"ok": False, "message": "Search query is empty."}
    webbrowser.open("https://www.google.com/search?q=" + quote_plus(query), new=2)
    return {"ok": True, "message": f"Google search opened for: {query}"}


def execute(payload: dict):
    if payload.get("token") != TOKEN:
        return {"ok": False, "message": "Unauthorized PC command."}
    action = str(payload.get("action", "")).lower().strip()
    target = str(payload.get("target", "")).strip()
    if action == "open_app":
        return open_app(target)
    if action == "open_website":
        return open_website(target)
    if action == "search_web":
        return search_web(target)
    return {"ok": False, "message": "PC action is not allowlisted."}


class Handler(BaseHTTPRequestHandler):
    def _headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._headers(204)

    def do_POST(self):
        if self.path != "/command":
            self._headers(404)
            self.wfile.write(b'{"ok":false,"message":"Not found."}')
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = execute(payload)
        except Exception as exc:
            result = {"ok": False, "message": f"PC bridge error: {type(exc).__name__}"}
        self._headers(200 if result.get("ok") else 400)
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        print("[MIRA-PC]", fmt % args)


if __name__ == "__main__":
    print(f"MIRA PC bridge running on http://{HOST}:{PORT}")
    print("Allowed: notepad, calculator, paint, explorer, cmd, Google, Gmail, YouTube, GitHub")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
