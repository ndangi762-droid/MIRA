import sqlite3
from pathlib import Path
from app.config import MEMORY_DB


class MemoryStore:
    """Local-first SQLite storage for chat history, sessions and long-term memory."""

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
            conn.execute(
                "CREATE TABLE IF NOT EXISTS sessions "
                "(id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT 'New chat', "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
            if "session_id" not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN session_id TEXT NOT NULL DEFAULT 'boss'")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id_id ON messages(session_id, id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC)")
            conn.execute(
                "INSERT OR IGNORE INTO sessions(id, title) VALUES ('boss', 'Main chat')"
            )

    def ensure_session(self, session_id: str, title: str = "New chat"):
        session_id = (session_id or "boss").strip() or "boss"
        with sqlite3.connect(MEMORY_DB) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions(id, title) VALUES (?, ?)",
                (session_id, title.strip() or "New chat"),
            )
            conn.execute(
                "UPDATE sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (session_id,),
            )

    def add(self, role: str, content: str, session_id: str = "boss"):
        self.ensure_session(session_id)
        with sqlite3.connect(MEMORY_DB) as conn:
            conn.execute(
                "INSERT INTO messages(session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )
            conn.execute(
                "UPDATE sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (session_id,),
            )

    def recent(self, limit: int = 8, session_id: str = "boss"):
        with sqlite3.connect(MEMORY_DB) as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

    def sessions(self, limit: int = 50):
        with sqlite3.connect(MEMORY_DB) as conn:
            rows = conn.execute(
                "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"id": sid, "title": title, "created_at": created, "updated_at": updated}
            for sid, title, created, updated in rows
        ]

    def rename_session(self, session_id: str, title: str):
        with sqlite3.connect(MEMORY_DB) as conn:
            conn.execute(
                "UPDATE sessions SET title=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (title.strip() or "New chat", session_id),
            )

    def delete_session(self, session_id: str):
        if session_id == "boss":
            return
        with sqlite3.connect(MEMORY_DB) as conn:
            conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))

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
