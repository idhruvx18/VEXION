"""
app/tools/open_app.py
──────────────────────
Tool: open_app — launch an allowlisted desktop application.

Only applications in the allowlist may be launched.
subprocess is called with a safe argument list — no shell=True.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Allowlist ─────────────────────────────────────────────────────────────────
# Maps friendly name → executable name (looked up on PATH or common locations).
# Users can extend this list in settings (future: persisted in SQLite).
APP_ALLOWLIST: dict[str, str] = {
    "notepad":         "notepad.exe",
    "calculator":      "calc.exe",
    "explorer":        "explorer.exe",
    "paint":           "mspaint.exe",
    "wordpad":         "wordpad.exe",
    "cmd":             "cmd.exe",
    "powershell":      "powershell.exe",
    "vs code":         "code.exe",
    "vscode":          "code.exe",
    "chrome":          "chrome.exe",
    "firefox":         "firefox.exe",
    "edge":            "msedge.exe",
    "spotify":         "spotify.exe",
    "discord":         "discord.exe",
    "task manager":    "taskmgr.exe",
    "control panel":   "control.exe",
    "snipping tool":   "SnippingTool.exe",
}


def list_allowed_apps() -> list[str]:
    return sorted(APP_ALLOWLIST.keys())


def open_app(app_name: str) -> dict:
    """
    Launch an allowlisted app.
    Returns {"ok": bool, "message": str}.
    """
    if not app_name or not isinstance(app_name, str):
        return {"ok": False, "message": "app_name must be a non-empty string."}

    key = app_name.strip().lower()
    exe = APP_ALLOWLIST.get(key)

    if exe is None:
        allowed = ", ".join(list_allowed_apps())
        return {
            "ok":      False,
            "message": (
                f"'{app_name}' is not in the allowed application list. "
                f"Allowed apps: {allowed}"
            ),
        }

    try:
        subprocess.Popen([exe], shell=False)   # noqa: S603 — exe is from allowlist only
        logger.info("Launched app: %s (%s)", app_name, exe)
        return {"ok": True, "message": f"Opened {app_name}."}
    except FileNotFoundError:
        msg = f"'{exe}' not found. The application may not be installed."
        logger.warning(msg)
        return {"ok": False, "message": msg}
    except Exception as exc:
        msg = f"Failed to launch '{app_name}': {exc}"
        logger.error(msg)
        return {"ok": False, "message": msg}
