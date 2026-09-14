"""MIRA PC Agent - small, local-only Windows command bridge."""
from __future__ import annotations

import json
import os
import subprocess
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
PORT = 8765
TOKEN = os.environ.get("MIRA_PC_TOKEN", "mira-local")

ALLOWED_URLS = {"youtube": "https://www.youtube.com/", "google": "https://www.google.com/", "gmail": "https://mail.google.com/"}
ALLOWED_APPS = {"notepad": ["notepad.exe"], "calculator": ["calc.exe"]}

def run_action(action: str, target: str = "") -> dict:
    action = (action or "").lower().strip(); target = (target or "").lower().strip()
    if action == "open_website" and target in ALLOWED_URLS:
        webbrowser.open(ALLOWED_URLS[target]); return {"ok": True, "message": f"Opened {target}."}
    if action == "open_app" and target in ALLOWED_APPS:
        subprocess.Popen(ALLOWED_APPS[target], shell=False); return {"ok": True, "message": f"Opened {target}."}
    return {"ok": False, "message": "Action not allowed."}

class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        if self.path != "/command": self._send(404, {"ok": False, "message": "Not found."}); return
        try:
            length = int(self.headers.get("Content-Length", "0")); data = json.loads(self.rfile.read(length) or b"{}")
            if data.get("token") != TOKEN: self._send(401, {"ok": False, "message": "Unauthorized."}); return
            self._send(200, run_action(data.get("action"), data.get("target")))
        except Exception as exc: self._send(400, {"ok": False, "message": str(exc)})
    def do_GET(self):
        self._send(200, {"ok": True, "service": "mira-pc-agent"}) if self.path == "/health" else self._send(404, {"ok": False, "message": "Not found."})
    def log_message(self, fmt, *args): print(f"[MIRA-PC] {fmt % args}")

if __name__ == "__main__":
    print(f"MIRA PC Agent listening on http://{HOST}:{PORT}")
    print("Allowed: YouTube, Google, Gmail, Notepad, Calculator")
    HTTPServer((HOST, PORT), Handler).serve_forever()
