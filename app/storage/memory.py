"""
app/storage/memory.py
──────────────────────
VEXION memory and settings persistence.

Provides:
  SettingsStore     — get/set user preferences
  ConversationStore — recent conversation history
  MemoryStore       — optional user-approved memories
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)


class SettingsStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return row["value"]

    def set(self, key: str, value: Any) -> None:
        serialised = json.dumps(value)
        self._conn.execute(
            "INSERT INTO settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, serialised),
        )
        self._conn.commit()

    def all(self) -> dict:
        rows = self._conn.execute("SELECT key, value FROM settings").fetchall()
        result = {}
        for row in rows:
            try:
                result[row["key"]] = json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                result[row["key"]] = row["value"]
        return result


class ConversationStore:
    """Stores recent conversation turns. Never stores raw audio or API keys."""

    MAX_HISTORY = 40    # keep last N turns in DB

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, role: str, content: str, provider: str = "") -> None:
        self._conn.execute(
            "INSERT INTO conversation_history (role, content, provider) VALUES (?,?,?)",
            (role, content, provider),
        )
        self._conn.commit()
        self._prune()

    def recent(self, n: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT role, content, provider, created_at "
            "FROM conversation_history ORDER BY id DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def clear(self) -> None:
        self._conn.execute("DELETE FROM conversation_history")
        self._conn.commit()
        logger.info("Conversation history cleared.")

    def _prune(self) -> None:
        self._conn.execute(
            "DELETE FROM conversation_history WHERE id NOT IN ("
            "  SELECT id FROM conversation_history ORDER BY id DESC LIMIT ?"
            ")",
            (self.MAX_HISTORY,),
        )
        self._conn.commit()


class MemoryStore:
    """Optional long-term memories (user-approved summaries only)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, summary: str, approved: bool = False) -> None:
        self._conn.execute(
            "INSERT INTO memories (summary, approved) VALUES (?,?)",
            (summary, int(approved)),
        )
        self._conn.commit()

    def approved(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, summary, created_at FROM memories WHERE approved=1"
        ).fetchall()
        return [dict(r) for r in rows]

    def all(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, summary, approved, created_at FROM memories"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete(self, memory_id: int) -> None:
        self._conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        self._conn.commit()

    def clear_all(self) -> None:
        self._conn.execute("DELETE FROM memories")
        self._conn.commit()
        logger.info("All memories cleared.")
