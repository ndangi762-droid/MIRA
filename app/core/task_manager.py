from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone

DB_PATH = os.getenv("MIRA_TASK_DB", "mira_tasks.db")


class TaskManager:
    """SQLite-backed task/reminder store. No external service required."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init(self):
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                priority TEXT NOT NULL DEFAULT 'normal',
                created_at TEXT NOT NULL,
                due_at TEXT,
                reminder_at TEXT,
                completed_at TEXT
            )""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(tasks)").fetchall()}
            if "due_at" not in columns:
                db.execute("ALTER TABLE tasks ADD COLUMN due_at TEXT")
            if "reminder_at" not in columns:
                db.execute("ALTER TABLE tasks ADD COLUMN reminder_at TEXT")
            db.commit()

    def add(self, title: str, priority: str = "normal", due_at: str | None = None,
            reminder_at: str | None = None) -> dict:
        title = title.strip()
        if not title:
            raise ValueError("task title cannot be empty")
        task = {
            "id": uuid.uuid4().hex[:10], "title": title, "status": "pending",
            "priority": priority if priority in {"low", "normal", "high"} else "normal",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "due_at": due_at, "reminder_at": reminder_at,
        }
        with self._connect() as db:
            db.execute(
                "INSERT INTO tasks(id,title,status,priority,created_at,due_at,reminder_at) VALUES(?,?,?,?,?,?,?)",
                (task["id"], task["title"], task["status"], task["priority"], task["created_at"], task["due_at"], task["reminder_at"]),
            )
            db.commit()
        return task

    def list(self, status: str = "pending") -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,title,status,priority,created_at,due_at,reminder_at,completed_at FROM tasks "
                "WHERE status=? ORDER BY CASE WHEN due_at IS NULL THEN 1 ELSE 0 END, due_at ASC, created_at DESC",
                (status,),
            ).fetchall()
        keys = ("id", "title", "status", "priority", "created_at", "due_at", "reminder_at", "completed_at")
        return [dict(zip(keys, row)) for row in rows]

    def due_or_reminders(self, now: str | None = None) -> list[dict]:
        now = now or datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,title,status,priority,created_at,due_at,reminder_at,completed_at FROM tasks "
                "WHERE status='pending' AND ((reminder_at IS NOT NULL AND reminder_at <= ?) OR (due_at IS NOT NULL AND due_at <= ?)) "
                "ORDER BY due_at ASC, reminder_at ASC", (now, now)
            ).fetchall()
        keys = ("id", "title", "status", "priority", "created_at", "due_at", "reminder_at", "completed_at")
        return [dict(zip(keys, row)) for row in rows]

    def complete(self, query: str) -> int:
        with self._connect() as db:
            rows = db.execute("SELECT id,title FROM tasks WHERE status='pending'").fetchall()
            matches = [r for r in rows if query.lower() in r[1].lower() or query == r[0]]
            if not matches:
                return 0
            now = datetime.now(timezone.utc).isoformat()
            for task_id, _ in matches:
                db.execute("UPDATE tasks SET status='completed',completed_at=? WHERE id=?", (now, task_id))
            db.commit()
            return len(matches)

    def clear_completed(self) -> int:
        with self._connect() as db:
            cur = db.execute("DELETE FROM tasks WHERE status='completed'")
            db.commit()
            return cur.rowcount
