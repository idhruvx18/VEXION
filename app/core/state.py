"""
app/core/state.py
─────────────────
VEXION application state machine.

States:
  IDLE        — waiting for input
  LISTENING   — microphone active, capturing speech
  THINKING    — AI provider processing
  SPEAKING    — TTS output in progress
  EXECUTING   — tool running
  NEEDS_APPROVAL — waiting for user to approve a high-risk action
  ERROR       — something went wrong; recovery message available
  OFFLINE     — no AI provider available
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Callable


class AppState(Enum):
    IDLE           = auto()
    LISTENING      = auto()
    THINKING       = auto()
    SPEAKING       = auto()
    EXECUTING      = auto()
    NEEDS_APPROVAL = auto()
    ERROR          = auto()
    OFFLINE        = auto()


# Human-readable labels shown in the UI
STATE_LABELS: dict[AppState, str] = {
    AppState.IDLE:           "READY",
    AppState.LISTENING:      "I'M LISTENING…",
    AppState.THINKING:       "THINKING…",
    AppState.SPEAKING:       "SPEAKING…",
    AppState.EXECUTING:      "EXECUTING…",
    AppState.NEEDS_APPROVAL: "AWAITING APPROVAL",
    AppState.ERROR:          "ERROR",
    AppState.OFFLINE:        "OFFLINE",
}

# Valid transitions — prevents illegal state jumps
_VALID_TRANSITIONS: dict[AppState, set[AppState]] = {
    AppState.IDLE:           {AppState.LISTENING, AppState.THINKING, AppState.EXECUTING,
                               AppState.ERROR, AppState.OFFLINE},
    AppState.LISTENING:      {AppState.THINKING, AppState.IDLE, AppState.ERROR},
    AppState.THINKING:       {AppState.SPEAKING, AppState.EXECUTING, AppState.NEEDS_APPROVAL,
                               AppState.IDLE, AppState.ERROR, AppState.OFFLINE},
    AppState.SPEAKING:       {AppState.IDLE, AppState.ERROR},
    AppState.EXECUTING:      {AppState.IDLE, AppState.SPEAKING, AppState.NEEDS_APPROVAL,
                               AppState.ERROR},
    AppState.NEEDS_APPROVAL: {AppState.EXECUTING, AppState.IDLE, AppState.ERROR},
    AppState.ERROR:          {AppState.IDLE, AppState.OFFLINE},
    AppState.OFFLINE:        {AppState.IDLE, AppState.ERROR},
}


class StateManager:
    """Manages VEXION's application state with observer callbacks."""

    def __init__(self) -> None:
        self._state: AppState = AppState.IDLE
        self._status_text: str = ""
        self._observers: list[Callable[[AppState, str], None]] = []

    # ── Properties ──────────────────────────────────────────────────────────
    @property
    def state(self) -> AppState:
        return self._state

    @property
    def label(self) -> str:
        return STATE_LABELS[self._state]

    @property
    def status_text(self) -> str:
        return self._status_text

    # ── Observers ────────────────────────────────────────────────────────────
    def add_observer(self, fn: Callable[[AppState, str], None]) -> None:
        """Register a callback fired on every state change."""
        self._observers.append(fn)

    def _notify(self) -> None:
        for fn in self._observers:
            try:
                fn(self._state, self._status_text)
            except Exception:
                pass  # never let a bad observer crash the state machine

    # ── Transitions ──────────────────────────────────────────────────────────
    def transition(self, new_state: AppState, status_text: str = "") -> bool:
        """
        Attempt a state transition.
        Returns True on success, False if the transition is invalid.
        """
        allowed = _VALID_TRANSITIONS.get(self._state, set())
        if new_state not in allowed:
            return False
        self._state = new_state
        self._status_text = status_text or STATE_LABELS[new_state]
        self._notify()
        return True

    def force_transition(self, new_state: AppState, status_text: str = "") -> None:
        """Bypass validation — use only for error recovery."""
        self._state = new_state
        self._status_text = status_text or STATE_LABELS[new_state]
        self._notify()

    # ── Convenience helpers ───────────────────────────────────────────────────
    def set_idle(self) -> None:
        self.force_transition(AppState.IDLE)

    def set_listening(self) -> None:
        self.transition(AppState.LISTENING)

    def set_thinking(self) -> None:
        self.transition(AppState.THINKING)

    def set_speaking(self) -> None:
        self.transition(AppState.SPEAKING)

    def set_executing(self, action_name: str = "") -> None:
        label = f"EXECUTING… {action_name}".strip()
        self.transition(AppState.EXECUTING, label)

    def set_error(self, message: str = "") -> None:
        self.force_transition(AppState.ERROR, message or "An error occurred.")

    def set_offline(self) -> None:
        self.force_transition(AppState.OFFLINE)

    def set_needs_approval(self, action_description: str = "") -> None:
        self.transition(AppState.NEEDS_APPROVAL, action_description)

    # ── Utility ───────────────────────────────────────────────────────────────
    def is_busy(self) -> bool:
        return self._state in {
            AppState.LISTENING, AppState.THINKING,
            AppState.SPEAKING, AppState.EXECUTING,
        }

    def __repr__(self) -> str:
        return f"StateManager(state={self._state.name}, text={self._status_text!r})"
