import sqlite3
from pathlib import Path
from app.config import MEMORY_DB

class MemoryStore:
    def __init__(self):
        Path(MEMORY_DB).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(MEMORY_DB) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS messages "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT, "
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
            )

    def add(self, role: str, content: str):
        with sqlite3.connect(MEMORY_DB) as conn:
            conn.execute("INSERT INTO messages(role, content) VALUES (?, ?)", (role, content))

    def recent(self, limit: int = 8):
        with sqlite3.connect(MEMORY_DB) as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]
