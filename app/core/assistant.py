"""
app/core/assistant.py
──────────────────────
VEXION Assistant core.

Runs in a QThread worker so the UI never blocks.
Orchestrates:
  - StateManager  (what VEXION is doing right now)
  - ProviderRouter (which AI provider handles the request)
  - ToolRegistry   (safe tool execution)
  - TTSManager     (voice output)
  - Storage        (conversation history + audit)
"""

from __future__ import annotations

import json
import logging
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThread, QThreadPool, Signal, Slot

from app.ai.base import Message
from app.core.router import ProviderRouter
from app.core.state import AppState, StateManager
from app.storage.audit_log import AuditLog
from app.storage.database import initialise as init_db
from app.storage.memory import ConversationStore, SettingsStore
from app.tools.registry import PendingApproval, ToolRegistry
from app.voice.tts import TTSManager

logger = logging.getLogger(__name__)


# ── Worker signals ─────────────────────────────────────────────────────────────
class WorkerSignals(QObject):
    response_ready   = Signal(str, str)   # (text, provider_name)
    tool_pending     = Signal(object)     # PendingApproval
    error            = Signal(str)
    state_changed    = Signal(object, str)  # (AppState, label)


# ── AI worker ─────────────────────────────────────────────────────────────────
class AIWorker(QRunnable):
    """Runs AI generation off the main thread."""

    def __init__(
        self,
        user_text: str,
        router: ProviderRouter,
        history: list[Message],
        signals: WorkerSignals,
    ) -> None:
        super().__init__()
        self.user_text = user_text
        self.router    = router
        self.history   = history
        self.signals   = signals
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        try:
            result = self.router.generate(self.user_text, self.history)
            self.signals.response_ready.emit(result.text, result.provider)
        except Exception as exc:
            logger.error("AIWorker error: %s", exc)
            self.signals.error.emit(str(exc))


# ── Assistant ──────────────────────────────────────────────────────────────────
class Assistant(QObject):
    """
    Central assistant object.
    Connects the UI (via signals/slots), the AI router, and the tool registry.
    """

    # Outgoing signals for the UI to listen to
    response_ready    = Signal(str)              # text to show/speak
    tool_needs_approval = Signal(object)         # PendingApproval → show overlay
    state_changed     = Signal(object, str)      # (AppState, label)

    def __init__(self) -> None:
        super().__init__()
        self._sm        = StateManager()
        self._router    = ProviderRouter()
        self._tools     = ToolRegistry()
        self._tts       = TTSManager()
        self._pool      = QThreadPool.globalInstance()
        self._signals   = WorkerSignals()
        self._pending: PendingApproval | None = None

        # DB
        self._db_conn   = init_db()
        self._settings  = SettingsStore(self._db_conn)
        self._conv      = ConversationStore(self._db_conn)
        self._audit     = AuditLog(self._db_conn)

        # Wire worker signals
        self._signals.response_ready.connect(self._on_ai_response)
        self._signals.error.connect(self._on_ai_error)

        # Propagate state changes
        self._sm.add_observer(lambda s, t: self.state_changed.emit(s, t))

    @property
    def state_manager(self) -> StateManager:
        return self._sm

    # ── Input entry point ─────────────────────────────────────────────────────
    @Slot(str)
    def handle_input(self, text: str) -> None:
        """Process a text (or transcribed voice) command."""
        text = text.strip()
        if not text:
            return

        self._sm.set_thinking()
        self._conv.add("user", text)

        # Build recent history for context (last 10 turns)
        history = [
            Message(role=m["role"], content=m["content"])
            for m in self._conv.recent(10)
            if m["role"] in ("user", "assistant")
        ]

        worker = AIWorker(
            user_text=text,
            router=self._router,
            history=history,
            signals=self._signals,
        )
        self._pool.start(worker)

    # ── AI response ───────────────────────────────────────────────────────────
    @Slot(str, str)
    def _on_ai_response(self, text: str, provider: str) -> None:
        # Try to parse a tool call from the response
        tool_call = ToolRegistry.parse_tool_call(text)

        if tool_call:
            tool_name, args = tool_call
            result = self._tools.dispatch(tool_name, args)

            if isinstance(result, PendingApproval):
                self._pending = result
                self._sm.set_needs_approval(result.request.description)
                self.tool_needs_approval.emit(result)
            else:
                self._finish_tool(tool_name, args, result)
        else:
            # Plain text response
            self._sm.set_speaking()
            self._conv.add("assistant", text, provider)
            self.response_ready.emit(text)
            self._speak(text)
            self._sm.set_idle()

    @Slot(str)
    def _on_ai_error(self, error: str) -> None:
        self._sm.set_error(f"AI error: {error}")
        self.response_ready.emit(f"Something went wrong: {error}")

    # ── Tool execution ────────────────────────────────────────────────────────
    def _finish_tool(self, tool_name: str, args: dict, result: dict) -> None:
        ok      = result.get("ok", False)
        message = result.get("message", "Done.")
        self._audit.log(tool_name, args, ok, message)

        self._sm.set_speaking()
        self.response_ready.emit(message)
        self._speak(message)
        self._sm.set_idle()

    @Slot()
    def on_approval_given(self) -> None:
        if self._pending is None:
            return
        pending = self._pending
        self._pending = None
        self._sm.set_executing(pending.request.tool_name)
        result = pending.execute()
        self._finish_tool(pending.request.tool_name, pending.args, result)

    @Slot()
    def on_approval_cancelled(self) -> None:
        if self._pending:
            self._audit.log(
                self._pending.request.tool_name,
                self._pending.args,
                False,
                "Cancelled by user",
            )
        self._pending = None
        self._sm.set_idle()
        self.response_ready.emit("Action cancelled.")

    # ── TTS ───────────────────────────────────────────────────────────────────
    def _speak(self, text: str) -> None:
        voice_enabled = self._settings.get("voice_output", True)
        if voice_enabled:
            self._tts.speak(text, blocking=False)

    # ── Diagnostics ──────────────────────────────────────────────────────────
    def get_diagnostics_text(self) -> str:
        d = self._router.diagnostics()
        tts_d = self._tts.diagnostics()
        lines = [
            "── VEXION Diagnostics ──────────────────────────",
            f"  Active AI provider : {d['active_provider']}",
            f"  Cloud enabled      : {d['cloud_enabled']}",
            "",
            "  Gemini",
            f"    Configured : {d['gemini']['configured']}",
            f"    Available  : {d['gemini']['available']}",
            f"    Key status : {d['gemini']['key_status']}",
            "",
            "  Ollama",
            f"    URL        : {d['ollama']['base_url']}",
            f"    Model      : {d['ollama']['model']}",
            f"    Running    : {d['ollama']['available']}",
            f"    Model OK   : {d['ollama'].get('model_installed', 'N/A')}",
            "",
            "  TTS",
            f"    ElevenLabs : {tts_d['elevenlabs_available']}",
            f"    System TTS : {tts_d['system_tts_available']}",
            f"    Active     : {tts_d['active_provider']}",
            "────────────────────────────────────────────────",
        ]
        return "\n".join(lines)
