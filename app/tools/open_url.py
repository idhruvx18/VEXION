"""
app/tools/open_url.py
──────────────────────
Tool: open_url — open a validated URL in the system default browser.

Security:
  - Only http:// and https:// schemes are allowed.
  - URL must parse correctly.
  - No file://, javascript://, data://, or other dangerous schemes.
"""

from __future__ import annotations

import logging
import re
import webbrowser
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Allowed schemes
_ALLOWED_SCHEMES = {"http", "https"}

# Very basic suspicious-pattern block list (loopback, metadata)
_BLOCKED_HOSTS = {
    "169.254.169.254",   # AWS metadata
    "metadata.google.internal",
}


def validate_url(url: str) -> tuple[bool, str]:
    """
    Return (ok, reason).
    ok=True means the URL is safe to open.
    """
    if not url or not isinstance(url, str):
        return False, "URL is empty."

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Could not parse the URL."

    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        return False, f"Scheme '{scheme}' is not allowed. Only http and https are permitted."

    host = (parsed.hostname or "").lower()
    if not host:
        return False, "URL has no host."

    if host in _BLOCKED_HOSTS:
        return False, f"Host '{host}' is blocked."

    # Reject bare IP ranges that look like internal/loopback
    if re.match(r"^127\.", host) or host == "localhost":
        # Allow localhost for developer convenience but log it
        logger.info("Opening localhost URL: %s", url)

    return True, "ok"


def open_url(url: str) -> dict:
    """
    Open a validated URL.
    Returns {"ok": bool, "message": str}.
    """
    ok, reason = validate_url(url)
    if not ok:
        logger.warning("open_url blocked: %s — %s", url, reason)
        return {"ok": False, "message": reason}

    try:
        webbrowser.open(url)
        logger.info("Opened URL: %s", url)
        return {"ok": True, "message": f"Opened {url}"}
    except Exception as exc:
        msg = f"Failed to open URL: {exc}"
        logger.error(msg)
        return {"ok": False, "message": msg}
