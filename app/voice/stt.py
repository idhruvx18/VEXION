"""
app/voice/stt.py
─────────────────
VEXION Speech-to-Text provider abstraction.

Uses SpeechRecognition library with the Google Web Speech API
(free, no key required for basic use) as the default backend.
A Whisper-based local backend is available as a future upgrade.

Listening runs in a background thread; results are returned via callback.
The microphone is only active while explicitly started.
Raw audio is NOT stored.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)

ResultCallback = Callable[[str], None]
ErrorCallback  = Callable[[str], None]


class STTManager:
    """
    Manages push-to-talk speech recognition.

    Usage:
        stt = STTManager()
        stt.start(on_result=handle_text, on_error=handle_err)
        ...
        stt.stop()
    """

    def __init__(self) -> None:
        self._listening   = False
        self._thread: threading.Thread | None = None
        self._stop_event  = threading.Event()
        self._sr_available = self._check_sr()

    @staticmethod
    def _check_sr() -> bool:
        try:
            import speech_recognition  # noqa: F401
            return True
        except ImportError:
            return False

    def is_available(self) -> bool:
        return self._sr_available

    def start(
        self,
        on_result: ResultCallback,
        on_error: ErrorCallback | None = None,
    ) -> None:
        if self._listening:
            return
        if not self._sr_available:
            if on_error:
                on_error(
                    "Speech recognition not available. "
                    "Install SpeechRecognition: pip install SpeechRecognition"
                )
            return

        self._stop_event.clear()
        self._listening = True
        self._thread = threading.Thread(
            target=self._listen_loop,
            args=(on_result, on_error),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._listening = False

    def _listen_loop(
        self,
        on_result: ResultCallback,
        on_error: ErrorCallback | None,
    ) -> None:
        try:
            import speech_recognition as sr  # type: ignore

            recogniser = sr.Recognizer()
            recogniser.pause_threshold = 1.0
            recogniser.energy_threshold = 300
            recogniser.dynamic_energy_threshold = True

            with sr.Microphone() as source:
                recogniser.adjust_for_ambient_noise(source, duration=0.5)
                logger.info("STT: listening started")
                while not self._stop_event.is_set():
                    try:
                        audio = recogniser.listen(source, timeout=5, phrase_time_limit=15)
                        if self._stop_event.is_set():
                            break
                        text = recogniser.recognize_google(audio)
                        if text:
                            on_result(text)
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError as exc:
                        msg = f"STT service error: {exc}"
                        logger.error(msg)
                        if on_error:
                            on_error(msg)
                        break
        except OSError as exc:
            msg = f"Microphone not available: {exc}"
            logger.error(msg)
            if on_error:
                on_error(msg)
        except Exception as exc:
            msg = f"STT error: {type(exc).__name__}: {exc}"
            logger.error(msg)
            if on_error:
                on_error(msg)
        finally:
            self._listening = False

    def diagnostics(self) -> dict:
        return {
            "sr_available": self._sr_available,
            "listening":    self._listening,
        }
