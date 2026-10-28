"""
app/storage/database.py
────────────────────────
VEXION SQLite database — schema, migrations, and connection management.

Schema version is tracked in the `schema_version` table so future
updates can migrate data without wiping it.

API keys and passwords are NEVER stored here.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from app.config import paths as paths_cfg

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 2


def _get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    db_path = db_path or paths_cfg.db_path
    paths_cfg.ensure_dirs()
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _schema_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        return row["version"] if row else 0
    except sqlite3.OperationalError:
        return 0


def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute("DELETE FROM schema_version")
    conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))


def initialise(db_path: Path | None = None) -> sqlite3.Connection:
    """Open the database, run any pending migrations, return a connection."""
    conn = _get_connection(db_path)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    ver = _schema_version(conn)
    if ver < 1:
        _apply_v1(conn)
    if ver < 2:
        _apply_v2(conn)
    logger.debug("DB schema at version %d", CURRENT_SCHEMA_VERSION)


def _apply_v1(conn: sqlite3.Connection) -> None:
    """Initial schema."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS conversation_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            role        TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            provider    TEXT,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS memories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            summary     TEXT    NOT NULL,
            approved    INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """)
    _set_schema_version(conn, 1)
    conn.commit()
    logger.info("DB migration: applied v1")


def _apply_v2(conn: sqlite3.Connection) -> None:
    """Add audit log table."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name   TEXT    NOT NULL,
            args_json   TEXT,
            result_ok   INTEGER,
            summary     TEXT,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """)
    _set_schema_version(conn, 2)
    conn.commit()
    logger.info("DB migration: applied v2")
