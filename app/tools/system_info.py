"""
app/tools/system_info.py
─────────────────────────
System information tools:
  - get_time      — current date and time from the system clock
  - diagnostics   — VEXION provider/config status
  - list_tools    — describe all available tools
"""

from __future__ import annotations

import datetime
import platform


def get_time() -> dict:
    """Return the current local date and time."""
    now = datetime.datetime.now()
    return {
        "ok":          True,
        "time":        now.strftime("%H:%M:%S"),
        "date":        now.strftime("%A, %d %B %Y"),
        "iso":         now.isoformat(),
        "message":     f"It's {now.strftime('%H:%M')} on {now.strftime('%A, %d %B %Y')}.",
    }


def get_diagnostics() -> dict:
    """Collect VEXION provider and system diagnostics (no secrets)."""
    from app.config import gemini, elevenlabs, ollama, paths

    return {
        "ok":          True,
        "platform":    platform.platform(),
        "python":      platform.python_version(),
        "gemini":      gemini.status(),
        "elevenlabs":  elevenlabs.status(),
        "ollama":      ollama.status(),
        "data_dir":    str(paths.data_dir),
        "message":     "Diagnostics collected. See details above.",
    }


def list_tools() -> dict:
    """Return a description of all available tools."""
    tools = [
        {"name": "get_time",     "description": "Tell the current date and time."},
        {"name": "open_url",     "description": "Open a website URL in the default browser."},
        {"name": "open_app",     "description": "Launch an allowlisted desktop application."},
        {"name": "search_files", "description": "Search for files in approved folders."},
        {"name": "open_file",    "description": "Open a file or folder with the default app."},
        {"name": "create_note",  "description": "Create a text note in the VEXION notes folder."},
        {"name": "diagnostics",  "description": "Show VEXION provider and config status."},
        {"name": "list_tools",   "description": "List all available tools (this command)."},
    ]
    names = ", ".join(t["name"] for t in tools)
    return {
        "ok":      True,
        "tools":   tools,
        "message": f"Available tools: {names}.",
    }
