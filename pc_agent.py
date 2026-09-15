"""MIRA Windows PC agent.

Run this on the Windows PC that MIRA is allowed to control. It polls the live
MIRA server and executes only explicit allowlisted desktop actions.
"""
from __future__ import annotations

import os
import subprocess
import time
import webbrowser
from urllib.parse import quote_plus

import requests
import pyautogui

MIRA_SERVER = os.getenv("MIRA_SERVER", "https://mira-premium.onrender.com").rstrip("/")
TOKEN = os.getenv("MIRA_PC_TOKEN", "mira-local")
POLL_SECONDS = max(1, float(os.getenv("MIRA_PC_POLL_SECONDS", "2")))

APP_COMMANDS = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "explorer": ["explorer.exe"],
    "chrome": ["cmd", "/c", "start", "", "chrome"],
    "task_manager": ["taskmgr.exe"],
}

SITES = {
    "https://www.youtube.com/", "https://mail.google.com/", "https://www.google.com/", "https://github.com/"
}


def open_app(name: str):
    command = APP_COMMANDS.get(name.lower().strip())
    if not command:
        return False, f"App '{name}' is not allowlisted."
    subprocess.Popen(command, shell=False)
    return True, f"{name.replace('_', ' ').title()} opened."


def open_url(url: str):
    if url not in SITES:
        return False, "Website is not allowlisted."
    webbrowser.open(url, new=2)
    return True, "Website opened."


def search_web(query: str):
    query = query.strip()
    if not query:
        return False, "Search query is empty."
    webbrowser.open("https://www.google.com/search?q=" + quote_plus(query), new=2)
    return True, f"Google search opened for: {query}"


def type_text(value: str):
    pyautogui.write(str(value), interval=0.01)
    return True, "Text typed."


def hotkey(keys):
    allowed = {"ctrl", "alt", "shift", "tab", "enter", "esc", "c", "v", "a", "s", "z", "y", "f4"}
    keys = [str(k).lower() for k in keys]
    if not keys or any(k not in allowed for k in keys):
        return False, "Hotkey is not allowlisted."
    pyautogui.hotkey(*keys)
    return True, "Keyboard shortcut executed."


def click(x, y):
    x, y = int(x), int(y)
    width, height = pyautogui.size()
    if not (0 <= x < width and 0 <= y < height):
        return False, "Click coordinates are outside the screen."
    pyautogui.click(x, y)
    return True, f"Clicked at {x}, {y}."


def execute(command: dict):
    action = str(command.get("action", "")).lower().strip()
    if action == "open_app": return open_app(str(command.get("target", "")))
    if action == "open_url": return open_url(str(command.get("target", "")))
    if action == "search_web": return search_web(str(command.get("target", "")))
    if action == "type_text": return type_text(str(command.get("text", "")))
    if action == "hotkey": return hotkey(command.get("keys", []))
    if action == "click": return click(command.get("x", -1), command.get("y", -1))
    return False, "PC action is not allowlisted."


def main():
    print(f"MIRA PC agent connected to {MIRA_SERVER}")
    print("Waiting for MIRA commands... (Ctrl+C to stop)")
    while True:
        try:
            response = requests.get(
                f"{MIRA_SERVER}/api/pc2/poll",
                params={"token": TOKEN, "device": "windows"}, timeout=15
            )
            response.raise_for_status()
            command = response.json().get("command")
            if command:
                ok, message = execute(command)
                print(f"[MIRA-PC] {message}")
                try:
                    requests.post(
                        f"{MIRA_SERVER}/api/pc2/ack",
                        params={"token": TOKEN, "command_id": command.get("id", ""), "ok": str(ok).lower(), "message": message}, timeout=10
                    )
                except requests.RequestException:
                    pass
        except requests.RequestException as exc:
            print(f"[MIRA-PC] Server connection error: {type(exc).__name__}")
        except KeyboardInterrupt:
            print("\nMIRA PC agent stopped.")
            return
        except Exception as exc:
            print(f"[MIRA-PC] Error: {type(exc).__name__}: {exc}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
