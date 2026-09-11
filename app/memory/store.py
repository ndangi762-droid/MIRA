import sqlite3
from pathlib import Path
from app.config import MEMORY_DB


class MemoryStore:
    """Small local-first SQLite memory layer for chat history and explicit memories."""

    def __init__(self):
        Path(MEMORY_DB).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(MEMORY_DB) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS messages "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL DEFAULT 'boss', "
                "role TEXT NOT NULL, content TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS memories "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL UNIQUE, "
                "value TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'general', "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            )
            # Existing databases from v2 did not have session_id.
            columns = {row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
            if "session_id" not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN session_id TEXT NOT NULL DEFAULT 'boss'")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id_id ON messages(session_id, id)")

    def add(self, role: str, content: str, session_id: str = "boss"):
        with sqlite3.connect(MEMORY_DB) as conn:
            conn.execute(
                "INSERT INTO messages(session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )

    def recent(self, limit: int = 8, session_id: str = "boss"):
        with sqlite3.connect(MEMORY_DB) as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

    def remember(self, key: str, value: str, category: str = "general"):
        with sqlite3.connect(MEMORY_DB) as conn:
            conn.execute(
                "INSERT INTO memories(key, value, category) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
                "category=excluded.category, updated_at=CURRENT_TIMESTAMP",
                (key.strip(), value.strip(), category.strip() or "general"),
            )

    def memories(self, limit: int = 50):
        with sqlite3.connect(MEMORY_DB) as conn:
            rows = conn.execute(
                "SELECT key, value, category, updated_at FROM memories "
                "ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"key": key, "value": value, "category": category, "updated_at": updated_at}
            for key, value, category, updated_at in rows
        ]

    def forget(self, key: str):
        with sqlite3.connect(MEMORY_DB) as conn:
            conn.execute("DELETE FROM memories WHERE key = ?", (key.strip(),))
