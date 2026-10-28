"""
app/tools/files.py
──────────────────
File-related tools for VEXION:
  - search_files  — search for files in approved directories
  - open_file     — open a file with the OS default handler
  - create_note   — create a plain-text note in the VEXION notes folder

Security:
  - File operations are restricted to approved root directories.
  - Path-traversal attacks (../) are detected and blocked.
  - Notes are written only to the dedicated VEXION notes folder.
  - No file is deleted or overwritten by these tools.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from app.config import paths as paths_cfg

logger = logging.getLogger(__name__)

# Approved roots for file search/open
# Users can add more in settings (future feature).
def _approved_roots() -> list[Path]:
    return [
        Path.home() / "Documents",
        Path.home() / "Desktop",
        Path.home() / "Downloads",
        paths_cfg.notes_dir,
    ]


def _is_safe_path(target: Path, roots: list[Path]) -> bool:
    """Return True if target is under at least one approved root."""
    try:
        resolved = target.resolve()
        for root in roots:
            try:
                resolved.relative_to(root.resolve())
                return True
            except ValueError:
                continue
    except Exception:
        pass
    return False


# ── Search files ──────────────────────────────────────────────────────────────
def search_files(query: str, root: str | None = None) -> dict:
    """
    Search for files whose names contain `query` inside approved directories.
    Returns up to 20 matches.
    """
    if not query or not isinstance(query, str):
        return {"ok": False, "message": "query must be a non-empty string.", "results": []}

    query = query.strip().lower()
    roots = _approved_roots()

    if root:
        custom_root = Path(root)
        if not _is_safe_path(custom_root, roots):
            return {
                "ok":      False,
                "message": f"'{root}' is outside the approved search directories.",
                "results": [],
            }
        roots = [custom_root]

    results: list[str] = []
    for r in roots:
        if not r.exists():
            continue
        try:
            for item in r.rglob("*"):
                if query in item.name.lower():
                    results.append(str(item))
                    if len(results) >= 20:
                        break
        except PermissionError:
            continue
        if len(results) >= 20:
            break

    if results:
        return {"ok": True, "message": f"Found {len(results)} file(s).", "results": results}
    return {"ok": True, "message": "No files found.", "results": []}


# ── Open file ─────────────────────────────────────────────────────────────────
def open_file(file_path: str) -> dict:
    """Open a file or folder with the OS default handler."""
    if not file_path:
        return {"ok": False, "message": "file_path must be a non-empty string."}

    target = Path(file_path)

    if not _is_safe_path(target, _approved_roots()):
        return {
            "ok":      False,
            "message": f"'{file_path}' is outside the approved directories.",
        }

    if not target.exists():
        return {"ok": False, "message": f"'{file_path}' does not exist."}

    try:
        os.startfile(str(target))   # Windows-specific; opens with default app
        return {"ok": True, "message": f"Opened '{target.name}'."}
    except AttributeError:
        # Non-Windows fallback (useful in tests)
        subprocess.Popen(["xdg-open", str(target)], shell=False)
        return {"ok": True, "message": f"Opened '{target.name}'."}
    except Exception as exc:
        return {"ok": False, "message": f"Failed to open file: {exc}"}


# ── Create note ───────────────────────────────────────────────────────────────
def create_note(title: str, content: str) -> dict:
    """
    Create a plain-text note in ~/VEXION_data/notes/.
    Title becomes the filename (sanitised).
    Returns {"ok": bool, "message": str, "path": str}.
    """
    if not title or not isinstance(title, str):
        return {"ok": False, "message": "title must be a non-empty string.", "path": ""}
    if not isinstance(content, str):
        content = ""

    # Sanitise filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
    safe_title = safe_title.strip()[:80] or "note"
    filename = f"{safe_title}.txt"

    try:
        paths_cfg.ensure_dirs()
        note_path = paths_cfg.notes_dir / filename

        if note_path.exists():
            # Append a counter to avoid overwriting
            counter = 1
            while note_path.exists():
                note_path = paths_cfg.notes_dir / f"{safe_title}_{counter}.txt"
                counter += 1

        note_path.write_text(content, encoding="utf-8")
        logger.info("Note created: %s", note_path)
        return {"ok": True, "message": f"Note saved as '{note_path.name}'.", "path": str(note_path)}
    except Exception as exc:
        msg = f"Failed to create note: {exc}"
        logger.error(msg)
        return {"ok": False, "message": msg, "path": ""}
