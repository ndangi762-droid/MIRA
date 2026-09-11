import os
import sqlite3
from datetime import datetime, timezone

DB_URL = os.getenv("DATABASE_URL", "").strip()
SQLITE_PATH = os.getenv("MIRA_MEMORY_DB", "/tmp/mira_memory.sqlite3")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _conn():
    if DB_URL:
        import psycopg
        return psycopg.connect(DB_URL)
    return sqlite3.connect(SQLITE_PATH)


def init_memory():
    conn = _conn()
    try:
        cur = conn.cursor()
        if DB_URL:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS mira_memory (
                    id BIGSERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    memory_key TEXT NOT NULL,
                    memory_value TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(session_id, memory_key)
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS mira_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    memory_key TEXT NOT NULL,
                    memory_value TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(session_id, memory_key)
                )
            """)
        conn.commit()
    finally:
        conn.close()


def save_memory(session_id: str, key: str, value: str, category: str = "general"):
    now = _now()
    conn = _conn()
    try:
        cur = conn.cursor()
        if DB_URL:
            cur.execute("""
                INSERT INTO mira_memory (session_id, memory_key, memory_value, category, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id, memory_key)
                DO UPDATE SET memory_value = EXCLUDED.memory_value,
                              category = EXCLUDED.category,
                              updated_at = EXCLUDED.updated_at
            """, (session_id, key, value, category, now, now))
        else:
            cur.execute("""
                INSERT INTO mira_memory (session_id, memory_key, memory_value, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, memory_key)
                DO UPDATE SET memory_value = excluded.memory_value,
                              category = excluded.category,
                              updated_at = excluded.updated_at
            """, (session_id, key, value, category, now, now))
        conn.commit()
    finally:
        conn.close()


def list_memories(session_id: str, limit: int = 50):
    conn = _conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if DB_URL else "?"
        cur.execute(
            f"SELECT memory_key, memory_value, category, updated_at FROM mira_memory WHERE session_id={placeholder} ORDER BY updated_at DESC LIMIT {int(limit)}",
            (session_id,),
        )
        rows = cur.fetchall()
        return [{"key": r[0], "value": r[1], "category": r[2], "updated_at": r[3]} for r in rows]
    finally:
        conn.close()


def delete_memory(session_id: str, key: str):
    conn = _conn()
    try:
        cur = conn.cursor()
        p = "%s" if DB_URL else "?"
        cur.execute(f"DELETE FROM mira_memory WHERE session_id={p} AND memory_key={p}", (session_id, key))
        conn.commit()
    finally:
        conn.close()
