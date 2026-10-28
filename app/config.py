"""
app/config.py
─────────────
Central configuration loader for VEXION.

Reads from environment variables (populated by python-dotenv from .env).
Never prints or logs full API key values.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ── Locate and load .env ────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent          # project root
_ENV_FILE = _ROOT / ".env"
_ENV_EXAMPLE = _ROOT / ".env.example"

load_dotenv(_ENV_FILE, override=False)        # does not override shell exports


# ── Helper ──────────────────────────────────────────────────────────────────
def _masked(value: str | None, show_chars: int = 4) -> str:
    """Return a masked representation — never the full key."""
    if not value:
        return "NOT SET"
    if len(value) <= show_chars:
        return "****"
    return f"...{value[-show_chars:]}"


def _get(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default) or default


# ── Gemini ──────────────────────────────────────────────────────────────────
class GeminiConfig:
    api_key: str | None = _get("GEMINI_API_KEY")
    model: str = _get("GEMINI_MODEL") or "gemini-1.5-flash"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def status(self) -> str:
        if self.is_configured:
            return f"Configured (key: {_masked(self.api_key)})"
        return "Not configured — set GEMINI_API_KEY in .env"


# ── ElevenLabs ──────────────────────────────────────────────────────────────
class ElevenLabsConfig:
    api_key: str | None = _get("ELEVENLABS_API_KEY")
    voice_id: str | None = _get("ELEVENLABS_VOICE_ID")
    model: str = "eleven_monolingual_v1"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.voice_id)

    def status(self) -> str:
        if not self.api_key:
            return "Not configured — set ELEVENLABS_API_KEY in .env"
        if not self.voice_id:
            return "API key set, but ELEVENLABS_VOICE_ID is missing — set it in .env"
        return f"Configured (key: {_masked(self.api_key)}, voice: {self.voice_id})"


# ── Ollama ───────────────────────────────────────────────────────────────────
class OllamaConfig:
    base_url: str = _get("OLLAMA_BASE_URL") or "http://localhost:11434"
    model: str = _get("OLLAMA_MODEL") or "qwen2.5:3b"

    def status(self) -> str:
        return f"URL: {self.base_url} | Model: {self.model}"


# ── VEXION paths ─────────────────────────────────────────────────────────────
class PathsConfig:
    data_dir: Path = Path(
        _get("VEXION_DATA_DIR") or Path.home() / "VEXION_data"
    )
    notes_dir: Path = data_dir / "notes"
    db_path: Path = data_dir / "vexion.db"
    audit_log: Path = data_dir / "audit.log"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.notes_dir.mkdir(parents=True, exist_ok=True)


# ── App behaviour ─────────────────────────────────────────────────────────────
class AppConfig:
    log_level: str = _get("VEXION_LOG_LEVEL") or "INFO"
    global_shortcut: str = "Alt+Space"
    voice_enabled: bool = True       # can be toggled at runtime
    cloud_enabled: bool = True       # sends requests to Gemini when True


# ── Singleton accessors ───────────────────────────────────────────────────────
gemini = GeminiConfig()
elevenlabs = ElevenLabsConfig()
ollama = OllamaConfig()
paths = PathsConfig()
app = AppConfig()


def print_status() -> None:
    """Print a human-readable config status (safe — no secrets)."""
    lines = [
        "── VEXION Configuration ──────────────────────",
        f"  Gemini     : {gemini.status()}",
        f"  ElevenLabs : {elevenlabs.status()}",
        f"  Ollama     : {ollama.status()}",
        f"  Data dir   : {paths.data_dir}",
        f"  Log level  : {app.log_level}",
        "──────────────────────────────────────────────",
    ]
    print("\n".join(lines))


def get_missing_env_hints() -> list[str]:
    """Return human-readable hints for any missing critical config."""
    hints: list[str] = []
    if not gemini.is_configured:
        hints.append("Gemini disabled — add GEMINI_API_KEY to .env for cloud AI.")
    if not elevenlabs.is_configured:
        hints.append(
            "ElevenLabs disabled — add ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID "
            "to .env for voice output."
        )
    return hints
