"""
app/storage/audit_log.py
─────────────────────────
VEXION tool execution audit log.

Logs: tool name, args (no secrets), result ok/fail, short summary.
Provides query and export for user inspection.
"""

from __future__ import annotations

import json
import logging
import sqlite3

logger = logging.getLogger(__name__)


class AuditLog:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def log(
        self,
        tool_name: str,
        args: dict,
        result_ok: bool,
        summary: str = "",
    ) -> None:
        # Scrub any keys that look like secrets before storing
        safe_args = {
            k: v for k, v in args.items()
            if "key" not in k.lower() and "token" not in k.lower()
               and "password" not in k.lower()
        }
        self._conn.execute(
            "INSERT INTO audit_log (tool_name, args_json, result_ok, summary) "
            "VALUES (?,?,?,?)",
            (tool_name, json.dumps(safe_args), int(result_ok), summary),
        )
        self._conn.commit()
        logger.debug("Audit: %s ok=%s", tool_name, result_ok)

    def recent(self, n: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, tool_name, args_json, result_ok, summary, created_at "
            "FROM audit_log ORDER BY id DESC LIMIT ?",
            (n,),
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            try:
                d["args"] = json.loads(d.pop("args_json", "{}") or "{}")
            except json.JSONDecodeError:
                d["args"] = {}
            results.append(d)
        return results

    def clear(self) -> None:
        self._conn.execute("DELETE FROM audit_log")
        self._conn.commit()
        logger.info("Audit log cleared.")
