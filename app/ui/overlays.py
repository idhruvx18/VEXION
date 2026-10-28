"""
app/ui/overlays.py
──────────────────
VEXION overlay widgets:
  - WaveformWidget     — minimal animated audio waveform
  - ApprovalOverlay    — compact confirm/cancel for high-risk actions
  - SettingsOverlay    — compact settings panel (Ctrl+,)
  - DiagnosticsOverlay — config/connectivity status (Ctrl+D)
"""

from __future__ import annotations

import math
import random
import time
from typing import Callable

from PySide6.QtCore import Qt, QTimer, QRectF, Signal
from PySide6.QtGui import (
    QColor, QPainter, QPainterPath, QPen, QBrush, QLinearGradient
)
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget, QScrollArea, QTextEdit,
    QCheckBox, QLineEdit, QSizePolicy
)

from app.core.state import AppState
from app.ui.theme import Colors, Fonts, Sizes, Timing


# ── Waveform ──────────────────────────────────────────────────────────────────
class WaveformWidget(QWidget):
    """
    Minimal animated waveform bar.
    When active=True the bars animate with simulated or real levels.
    When active=False bars decay to flat.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._bars = 28
        self._levels: list[float] = [0.08] * self._bars
        self._active = False
        self._state: AppState = AppState.IDLE

        self.setFixedSize(Sizes.WAVEFORM_WIDTH, Sizes.WAVEFORM_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(Timing.WAVE_FRAME)

    def set_state(self, state: AppState) -> None:
        self._state = state
        self._active = state in (AppState.LISTENING, AppState.SPEAKING)

    def push_level(self, level: float) -> None:
        """Feed a real [0..1] amplitude from the audio pipeline."""
        self._levels.pop(0)
        self._levels.append(min(1.0, max(0.0, level)))

    def _tick(self) -> None:
        if self._active:
            # Simulated unless real audio is piped in
            t = time.monotonic()
            for i in range(self._bars):
                phase = t * 4.0 + i * 0.4
                sim = (math.sin(phase) + 1) / 2 * 0.6 + 0.1
                self._levels[i] = sim
        else:
            # Decay to flat
            self._levels = [max(0.05, v * 0.88) for v in self._levels]
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bar_w = (w - 2) / self._bars
        gap = bar_w * 0.25

        color = Colors.WAVE_COLOR if self._active else QColor(0, 140, 200, 80)

        for i, level in enumerate(self._levels):
            bar_h = max(3, level * (h - 4))
            x = i * bar_w + gap / 2
            y = (h - bar_h) / 2
            path = QPainterPath()
            rw = bar_w - gap
            rr = rw / 2
            path.addRoundedRect(QRectF(x, y, rw, bar_h), rr, rr)
            p.setBrush(QBrush(color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(path)
        p.end()


# ── Glassmorphism frame base ──────────────────────────────────────────────────
class GlassFrame(QFrame):
    """Base glass-style overlay frame."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(10, 18, 48, 0.88);
                border: 1px solid rgba(0, 160, 255, 0.35);
                border-radius: 12px;
            }}
            QLabel {{
                background: transparent;
                color: rgb(220, 240, 255);
                border: none;
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 6px 18px;
                font-family: "Segoe UI";
                font-size: 11px;
                letter-spacing: 2px;
            }}
        """)


# ── Approval overlay ──────────────────────────────────────────────────────────
class ApprovalOverlay(GlassFrame):
    """
    Compact overlay shown when VEXION needs the user to approve a
    potentially risky action before it runs.
    """

    approved = Signal()
    cancelled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(Sizes.OVERLAY_WIDTH, Sizes.OVERLAY_HEIGHT)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        # Header
        hdr = QLabel("APPROVAL REQUIRED")
        hdr.setFont(Fonts.overlay_title())
        hdr.setStyleSheet("color: rgb(255, 180, 40); letter-spacing: 3px;")
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hdr)

        # Action description
        self._action_label = QLabel("")
        self._action_label.setFont(Fonts.state_label(12))
        self._action_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._action_label.setWordWrap(True)
        self._action_label.setStyleSheet("color: rgb(200, 220, 255);")
        layout.addWidget(self._action_label)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        self._cancel_btn = QPushButton("CANCEL")
        self._cancel_btn.setFont(Fonts.button())
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(180, 40, 40, 0.4);
                color: rgb(255, 160, 160);
                border: 1px solid rgba(220, 60, 60, 0.6);
            }
            QPushButton:hover { background: rgba(200, 60, 60, 0.6); }
        """)
        self._cancel_btn.clicked.connect(self._on_cancel)

        self._approve_btn = QPushButton("APPROVE")
        self._approve_btn.setFont(Fonts.button())
        self._approve_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 160, 100, 0.4);
                color: rgb(140, 255, 200);
                border: 1px solid rgba(0, 200, 140, 0.6);
            }
            QPushButton:hover { background: rgba(0, 190, 120, 0.6); }
        """)
        self._approve_btn.clicked.connect(self._on_approve)

        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._approve_btn)
        layout.addLayout(btn_row)

    def show_action(self, description: str) -> None:
        self._action_label.setText(description)
        self.show()
        self._approve_btn.setFocus()

    def _on_approve(self) -> None:
        self.hide()
        self.approved.emit()

    def _on_cancel(self) -> None:
        self.hide()
        self.cancelled.emit()


# ── Diagnostics overlay ───────────────────────────────────────────────────────
class DiagnosticsOverlay(GlassFrame):
    """Displays provider config status. Opened with Ctrl+D."""

    closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(560)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)

        hdr = QLabel("DIAGNOSTICS")
        hdr.setFont(Fonts.overlay_title(14))
        hdr.setStyleSheet("color: rgb(0, 200, 255); letter-spacing: 4px;")
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hdr)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(Fonts.hud(10))
        self._text.setStyleSheet("""
            QTextEdit {
                background: rgba(0, 10, 30, 0.7);
                color: rgb(180, 220, 255);
                border: 1px solid rgba(0, 100, 200, 0.3);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        self._text.setFixedHeight(260)
        layout.addWidget(self._text)

        close_btn = QPushButton("CLOSE  [Ctrl+D]")
        close_btn.setFont(Fonts.button())
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 100, 200, 0.3);
                color: rgb(160, 210, 255);
                border: 1px solid rgba(0, 160, 255, 0.4);
            }
            QPushButton:hover { background: rgba(0, 140, 255, 0.4); }
        """)
        close_btn.clicked.connect(self._close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def show_diagnostics(self, text: str) -> None:
        self._text.setPlainText(text)
        self.show()
        self.adjustSize()

    def _close(self) -> None:
        self.hide()
        self.closed.emit()


# ── Settings overlay ──────────────────────────────────────────────────────────
class SettingsOverlay(GlassFrame):
    """Compact settings panel. Opened with Ctrl+, """

    closed = Signal()
    settings_changed = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(480)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)

        hdr = QLabel("SETTINGS")
        hdr.setFont(Fonts.overlay_title(14))
        hdr.setStyleSheet("color: rgb(0, 200, 255); letter-spacing: 4px;")
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hdr)

        # Voice toggle
        self._voice_cb = QCheckBox("  Enable voice input (microphone)")
        self._voice_cb.setFont(Fonts.state_label(11))
        self._voice_cb.setStyleSheet("color: rgb(200, 220, 255); spacing: 8px;")
        self._voice_cb.setChecked(True)
        layout.addWidget(self._voice_cb)

        # TTS toggle
        self._tts_cb = QCheckBox("  Enable voice output (TTS)")
        self._tts_cb.setFont(Fonts.state_label(11))
        self._tts_cb.setStyleSheet("color: rgb(200, 220, 255); spacing: 8px;")
        self._tts_cb.setChecked(True)
        layout.addWidget(self._tts_cb)

        # Cloud AI toggle
        self._cloud_cb = QCheckBox("  Enable cloud AI (Gemini)")
        self._cloud_cb.setFont(Fonts.state_label(11))
        self._cloud_cb.setStyleSheet("color: rgb(200, 220, 255); spacing: 8px;")
        self._cloud_cb.setChecked(True)
        layout.addWidget(self._cloud_cb)

        # Shortcut hint
        hint = QLabel("Shortcut to focus VEXION:  Alt+Space")
        hint.setFont(Fonts.hud(9))
        hint.setStyleSheet("color: rgb(100, 140, 180);")
        layout.addWidget(hint)

        layout.addStretch()

        save_btn = QPushButton("SAVE  [Ctrl+,]")
        save_btn.setFont(Fonts.button())
        save_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 100, 200, 0.3);
                color: rgb(160, 210, 255);
                border: 1px solid rgba(0, 160, 255, 0.4);
            }
            QPushButton:hover { background: rgba(0, 140, 255, 0.4); }
        """)
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _save(self) -> None:
        self.settings_changed.emit({
            "voice_input": self._voice_cb.isChecked(),
            "voice_output": self._tts_cb.isChecked(),
            "cloud_ai": self._cloud_cb.isChecked(),
        })
        self.hide()
        self.closed.emit()

    def load_settings(self, settings: dict) -> None:
        self._voice_cb.setChecked(settings.get("voice_input", True))
        self._tts_cb.setChecked(settings.get("voice_output", True))
        self._cloud_cb.setChecked(settings.get("cloud_ai", True))
        self.show()
