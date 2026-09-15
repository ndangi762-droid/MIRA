"""MIRA Windows PC bridge.

Run this ON THE USER'S WINDOWS PC. It polls the live MIRA server for
allowlisted computer actions, so the browser never needs direct localhost
access. No arbitrary shell commands are accepted.
"""
from __future__ import annotations

import os
import subprocess
import time
import webbrowser
import requests
from urllib.parse import quote_plus

MIRA_SERVER = os.getenv("MIRA_SERVER", "https://mira-premium.onrender.com").rstrip("/")
TOKEN = os.getenv("MIRA_PC_TOKEN", "mira-local")
POLL_SECONDS = max(1, float(os.getenv("MIRA_PC_POLL_SECONDS", "2")))

APP_COMMANDS = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "explorer": ["explorer.exe"],
    "cmd": ["cmd.exe"],
}


def open_app(name: str):
    command = APP_COMMANDS.get(name.lower().strip())
    if not command:
        return False, f"App '{name}' is not allowlisted."
    subprocess.Popen(command, shell=False)
    return True, f"{name.title()} opened."


def open_website(target: str):
    sites = {
        "google": "https://www.google.com/",
        "gmail": "https://mail.google.com/",
        "youtube": "https://www.youtube.com/",
        "github": "https://github.com/",
    }
    url = sites.get(target.lower().strip())
    if not url:
        return False, "Website is not allowlisted."
    webbrowser.open(url, new=2)
    return True, f"{target.title()} opened."


def search_web(query: str):
    query = query.strip()
    if not query:
        return False, "Search query is empty."
    webbrowser.open("https://www.google.com/search?q=" + quote_plus(query), new=2)
    return True, f"Google search opened for: {query}"


def execute(command: dict):
    action = str(command.get("action", "")).lower().strip()
    target = str(command.get("target", "")).strip()
    if action == "open_app":
        return open_app(target)
    if action == "open_website":
        return open_website(target)
    if action == "search_web":
        return search_web(target)
    return False, "PC action is not allowlisted."


def main():
    print(f"MIRA PC agent connected to {MIRA_SERVER}")
    print("Waiting for MIRA commands... (Ctrl+C to stop)")
    while True:
        try:
            response = requests.get(
                f"{MIRA_SERVER}/api/pc/poll",
                params={"token": TOKEN},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            command = payload.get("command")
            if command:
                ok, message = execute(command)
                print(f"[MIRA-PC] {message}")
                try:
                    requests.post(
                        f"{MIRA_SERVER}/api/pc/ack",
                        params={"token": TOKEN, "command_id": command.get("id", ""), "ok": str(ok).lower(), "message": message},
                        timeout=10,
                    )
                except requests.RequestException:
                    pass
        except requests.RequestException as exc:
            print(f"[MIRA-PC] Server connection error: {type(exc).__name__}")
        except KeyboardInterrupt:
            print("\nMIRA PC agent stopped.")
            return
        except Exception as exc:
            print(f"[MIRA-PC] Error: {type(exc).__name__}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
