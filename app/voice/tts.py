"""
app/voice/tts.py
─────────────────
VEXION Text-to-Speech provider abstraction.

Providers (in priority order):
  1. ElevenLabs — primary, requires ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID
  2. System pyttsx3 / SAPI — local Windows fallback (no internet required)

Both providers run audio playback in a background thread so the UI never
freezes. Raw audio is played from memory; nothing is written to disk unless
explicitly requested.
"""

from __future__ import annotations

import io
import logging
import threading
from abc import ABC, abstractmethod

from app.config import elevenlabs as el_cfg

logger = logging.getLogger(__name__)


# ── Base ──────────────────────────────────────────────────────────────────────
class TTSProvider(ABC):
    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def speak(self, text: str, blocking: bool = False) -> None:
        """Speak text.  If blocking=False, runs in a daemon thread."""


# ── ElevenLabs ────────────────────────────────────────────────────────────────
class ElevenLabsTTS(TTSProvider):
    name = "elevenlabs"

    def is_available(self) -> bool:
        return el_cfg.is_configured

    def speak(self, text: str, blocking: bool = False) -> None:
        if not self.is_available():
            logger.warning(
                "ElevenLabs TTS not configured. "
                "Add ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID to .env."
            )
            return

        def _run() -> None:
            try:
                from elevenlabs import generate, play, set_api_key, Voice  # type: ignore
                set_api_key(el_cfg.api_key)
                audio = generate(
                    text=text,
                    voice=el_cfg.voice_id,
                    model=el_cfg.model,
                )
                play(audio)
            except ImportError:
                logger.error("elevenlabs package not installed.")
            except Exception as exc:
                logger.error("ElevenLabs TTS error: %s", type(exc).__name__)

        if blocking:
            _run()
        else:
            t = threading.Thread(target=_run, daemon=True)
            t.start()


# ── System TTS fallback (pyttsx3 / Windows SAPI) ─────────────────────────────
class SystemTTS(TTSProvider):
    name = "system_tts"

    def __init__(self) -> None:
        self._engine = None
        self._lock = threading.Lock()
        self._init()

    def _init(self) -> None:
        try:
            import pyttsx3  # type: ignore
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", 175)
            self._engine.setProperty("volume", 0.9)
        except ImportError:
            logger.info("pyttsx3 not installed — system TTS unavailable.")
        except Exception as exc:
            logger.warning("System TTS init failed: %s", exc)

    def is_available(self) -> bool:
        return self._engine is not None

    def speak(self, text: str, blocking: bool = False) -> None:
        if not self.is_available():
            logger.warning("System TTS unavailable.")
            return

        def _run() -> None:
            with self._lock:
                try:
                    self._engine.say(text)
                    self._engine.runAndWait()
                except Exception as exc:
                    logger.error("System TTS error: %s", exc)

        if blocking:
            _run()
        else:
            t = threading.Thread(target=_run, daemon=True)
            t.start()


# ── TTS Manager — picks the best available provider ───────────────────────────
class TTSManager:
    """
    Picks ElevenLabs if configured, falls back to system TTS,
    and degrades gracefully if neither is available (silent fallback).
    """

    def __init__(self) -> None:
        self._elevenlabs = ElevenLabsTTS()
        self._system     = SystemTTS()

    def active_provider(self) -> TTSProvider | None:
        if self._elevenlabs.is_available():
            return self._elevenlabs
        if self._system.is_available():
            return self._system
        return None

    def speak(self, text: str, blocking: bool = False) -> None:
        provider = self.active_provider()
        if provider is None:
            logger.info(
                "No TTS provider available. "
                "Configure ElevenLabs or install pyttsx3 for voice output."
            )
            return
        provider.speak(text, blocking=blocking)

    def is_available(self) -> bool:
        return self.active_provider() is not None

    def diagnostics(self) -> dict:
        return {
            "elevenlabs_available": self._elevenlabs.is_available(),
            "system_tts_available": self._system.is_available(),
            "active_provider":      (
                p.name if (p := self.active_provider()) else "none"
            ),
        }
