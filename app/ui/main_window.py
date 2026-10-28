"""
app/ui/main_window.py
──────────────────────
VEXION main window.

Full-screen borderless dark window.
Layout (top to bottom):
  HUD row (wordmark + clock/status)
  ──── generous space ────
  Orb (centre hero)
  Wordmark "VEXION" + tagline
  State label
  Waveform
  Command input (always visible, minimal)
  ──── spacer ────
  Bottom bar (status line)

Keyboard shortcuts:
  Alt+Space   — focus command input / toggle listen
  Escape      — exit full-screen → windowed; second Esc minimises
  Ctrl+,      — settings overlay
  Ctrl+D      — diagnostics overlay
  Ctrl+Q      — quit
"""

from __future__ import annotations

import datetime
from typing import Callable

from PySide6.QtCore import (
    Qt, QTimer, Signal, Slot, QSize, QPoint, QRect
)
from PySide6.QtGui import (
    QColor, QKeySequence, QLinearGradient,
    QPainter, QPainterPath, QBrush, QShortcut, QFont
)
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget, QGraphicsOpacityEffect
)

from app.core.state import AppState, StateManager, STATE_LABELS
from app.ui.orb_widget import OrbWidget
from app.ui.overlays import (
    WaveformWidget, ApprovalOverlay,
    DiagnosticsOverlay, SettingsOverlay
)
from app.ui.theme import Colors, Fonts, Sizes, Timing


class MainWindow(QWidget):
    """VEXION main full-screen window."""

    # Signals to the assistant core
    text_submitted = Signal(str)          # user hit Enter on command input
    listen_toggled = Signal(bool)         # True = start listening
    settings_changed = Signal(dict)
    approval_given = Signal()
    approval_cancelled = Signal()

    def __init__(self, state_manager: StateManager | None = None) -> None:
        super().__init__()
        self._sm = state_manager or StateManager()
        self._sm.add_observer(self._on_state_change)
        self._fullscreen = True

        self._build_window()
        self._build_layout()
        self._build_overlays()
        self._build_shortcuts()
        self._start_clock()

    # ── Window setup ─────────────────────────────────────────────────────────
    def _build_window(self) -> None:
        self.setWindowTitle("VEXION")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgb({Colors.BG_DEEP.red()},
                                       {Colors.BG_DEEP.green()},
                                       {Colors.BG_DEEP.blue()});
            }}
            QLineEdit {{
                background: rgba(0, 20, 50, 0.7);
                color: rgb(220, 240, 255);
                border: 1px solid rgba(0, 160, 255, 0.4);
                border-radius: 22px;
                padding: 0 20px;
                selection-background-color: rgba(0, 160, 255, 0.4);
            }}
            QLineEdit:focus {{
                border: 1px solid rgba(0, 200, 255, 0.8);
                background: rgba(0, 25, 60, 0.85);
            }}
        """)
        self.showFullScreen()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build_layout(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── HUD row ──────────────────────────────────────────────────────────
        hud = QHBoxLayout()
        hud.setContentsMargins(32, 20, 32, 0)

        self._wordmark_hud = QLabel("VEXION")
        self._wordmark_hud.setFont(Fonts.hud(10))
        self._wordmark_hud.setStyleSheet(
            "color: rgba(0,200,255,0.8); letter-spacing: 5px;"
        )

        self._clock_label = QLabel("")
        self._clock_label.setFont(Fonts.hud(9))
        self._clock_label.setStyleSheet("color: rgba(100,140,180,0.8);")
        self._clock_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        self._online_dot = QLabel("● ONLINE")
        self._online_dot.setFont(Fonts.hud(9))
        self._online_dot.setStyleSheet(
            f"color: rgb({Colors.STATE_ONLINE.red()},"
            f"{Colors.STATE_ONLINE.green()},"
            f"{Colors.STATE_ONLINE.blue()}); letter-spacing: 2px;"
        )

        hud.addWidget(self._wordmark_hud)
        hud.addStretch()
        hud.addWidget(self._clock_label)
        hud.addSpacing(20)
        hud.addWidget(self._online_dot)
        root.addLayout(hud)

        # ── Top spacer ────────────────────────────────────────────────────────
        root.addStretch(2)

        # ── Orb ───────────────────────────────────────────────────────────────
        orb_row = QHBoxLayout()
        self._orb = OrbWidget()
        self._orb.setFixedSize(Sizes.ORB_DIAMETER, Sizes.ORB_DIAMETER)
        self._orb.clicked.connect(self._on_orb_click)
        orb_row.addStretch()
        orb_row.addWidget(self._orb)
        orb_row.addStretch()
        root.addLayout(orb_row)

        # ── Under-orb spacer ──────────────────────────────────────────────────
        root.addSpacing(28)

        # ── Wordmark ──────────────────────────────────────────────────────────
        self._wordmark = QLabel("VEXION")
        self._wordmark.setFont(Fonts.wordmark(32))
        self._wordmark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wordmark.setStyleSheet("color: rgb(200,230,255); letter-spacing: 14px;")
        root.addWidget(self._wordmark)

        root.addSpacing(6)

        # ── Tagline ───────────────────────────────────────────────────────────
        self._tagline = QLabel("THINK.  EXECUTE.  VERIFY.")
        self._tagline.setFont(Fonts.tagline(10))
        self._tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tagline.setStyleSheet("color: rgba(100,160,220,0.7); letter-spacing: 6px;")
        root.addWidget(self._tagline)

        root.addSpacing(18)

        # ── State label ───────────────────────────────────────────────────────
        self._state_label = QLabel("READY")
        self._state_label.setFont(Fonts.state_label(12))
        self._state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._state_label.setStyleSheet("color: rgba(0,200,255,0.85); letter-spacing: 4px;")
        root.addWidget(self._state_label)

        root.addSpacing(10)

        # ── Waveform ──────────────────────────────────────────────────────────
        wave_row = QHBoxLayout()
        self._waveform = WaveformWidget()
        wave_row.addStretch()
        wave_row.addWidget(self._waveform)
        wave_row.addStretch()
        root.addLayout(wave_row)

        root.addSpacing(20)

        # ── Command input ─────────────────────────────────────────────────────
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)

        self._input = QLineEdit()
        self._input.setFont(Fonts.command_input())
        self._input.setPlaceholderText("Type a command or press Alt+Space to speak…")
        self._input.setFixedSize(Sizes.INPUT_WIDTH, Sizes.INPUT_HEIGHT)
        self._input.returnPressed.connect(self._on_input_submitted)

        self._mic_btn = QPushButton("🎤")
        self._mic_btn.setFixedSize(44, 44)
        self._mic_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 80, 160, 0.5);
                border: 1px solid rgba(0, 160, 255, 0.5);
                border-radius: 22px;
                font-size: 16px;
                color: white;
            }
            QPushButton:hover { background: rgba(0, 120, 200, 0.7); }
            QPushButton:checked { background: rgba(0, 200, 255, 0.4); }
        """)
        self._mic_btn.setCheckable(True)
        self._mic_btn.clicked.connect(self._on_mic_toggle)

        input_row.addStretch()
        input_row.addWidget(self._input)
        input_row.addSpacing(10)
        input_row.addWidget(self._mic_btn)
        input_row.addStretch()
        root.addLayout(input_row)

        root.addStretch(3)

        # ── Bottom bar ────────────────────────────────────────────────────────
        bottom = QHBoxLayout()
        bottom.setContentsMargins(32, 0, 32, 16)

        self._status_left = QLabel("● ONLINE")
        self._status_left.setFont(Fonts.hud(8))
        self._status_left.setStyleSheet(
            f"color: rgb({Colors.STATE_ONLINE.red()},"
            f"{Colors.STATE_ONLINE.green()},"
            f"{Colors.STATE_ONLINE.blue()}); letter-spacing: 2px;"
        )

        self._status_right = QLabel("PRIVATE  |  POWERFUL  |  PERSONAL")
        self._status_right.setFont(Fonts.hud(8))
        self._status_right.setStyleSheet("color: rgba(80,120,160,0.6); letter-spacing: 3px;")

        bottom.addWidget(self._status_left)
        bottom.addStretch()
        bottom.addWidget(self._status_right)
        root.addLayout(bottom)

    # ── Overlays ──────────────────────────────────────────────────────────────
    def _build_overlays(self) -> None:
        self._approval = ApprovalOverlay(self)
        self._approval.approved.connect(self.approval_given)
        self._approval.cancelled.connect(self.approval_cancelled)

        self._diagnostics = DiagnosticsOverlay(self)
        self._settings_ov = SettingsOverlay(self)
        self._settings_ov.settings_changed.connect(self.settings_changed)

        self._centre_overlay(self._approval)
        self._centre_overlay(self._diagnostics)
        self._centre_overlay(self._settings_ov)

    def _centre_overlay(self, widget: QWidget) -> None:
        widget.hide()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Keep overlays centred
        for ov in (self._approval, self._diagnostics, self._settings_ov):
            if ov.isVisible():
                self._reposition_overlay(ov)

    def _reposition_overlay(self, ov: QWidget) -> None:
        x = (self.width()  - ov.width())  // 2
        y = (self.height() - ov.height()) // 2
        ov.move(x, y)

    # ── Shortcuts ─────────────────────────────────────────────────────────────
    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("Escape"), self).activated.connect(self._on_escape)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(QApplication.instance().quit)
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(self._toggle_settings)
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(self._toggle_diagnostics)
        QShortcut(QKeySequence("Alt+Space"), self).activated.connect(self._on_alt_space)

    # ── Clock ─────────────────────────────────────────────────────────────────
    def _start_clock(self) -> None:
        self._update_clock()
        t = QTimer(self)
        t.timeout.connect(self._update_clock)
        t.start(1000)

    def _update_clock(self) -> None:
        now = datetime.datetime.now()
        self._clock_label.setText(now.strftime("%H:%M   %a %d %b"))

    # ── State observer ────────────────────────────────────────────────────────
    @Slot(object, str)
    def _on_state_change(self, state: AppState, text: str) -> None:
        self._state_label.setText(text or STATE_LABELS[state])
        self._orb.set_state(state)
        self._waveform.set_state(state)

        # Mic button visual sync
        self._mic_btn.setChecked(state == AppState.LISTENING)

        # Online indicator
        if state == AppState.OFFLINE:
            self._set_offline_indicator()
        elif state == AppState.ERROR:
            self._status_left.setText("● ERROR")
            self._status_left.setStyleSheet(
                f"color: rgb({Colors.STATE_OFFLINE.red()},"
                f"{Colors.STATE_OFFLINE.green()},"
                f"{Colors.STATE_OFFLINE.blue()}); letter-spacing: 2px;"
            )
        else:
            self._status_left.setText("● ONLINE")
            self._status_left.setStyleSheet(
                f"color: rgb({Colors.STATE_ONLINE.red()},"
                f"{Colors.STATE_ONLINE.green()},"
                f"{Colors.STATE_ONLINE.blue()}); letter-spacing: 2px;"
            )

        # Approval overlay
        if state == AppState.NEEDS_APPROVAL:
            self._approval.show_action(text)
            self._reposition_overlay(self._approval)

    def _set_offline_indicator(self) -> None:
        self._online_dot.setText("● OFFLINE")
        self._online_dot.setStyleSheet(
            f"color: rgb({Colors.STATE_OFFLINE.red()},"
            f"{Colors.STATE_OFFLINE.green()},"
            f"{Colors.STATE_OFFLINE.blue()}); letter-spacing: 2px;"
        )
        self._status_left.setText("● OFFLINE")
        self._status_left.setStyleSheet(
            f"color: rgb({Colors.STATE_OFFLINE.red()},"
            f"{Colors.STATE_OFFLINE.green()},"
            f"{Colors.STATE_OFFLINE.blue()}); letter-spacing: 2px;"
        )

    # ── Input handlers ────────────────────────────────────────────────────────
    def _on_input_submitted(self) -> None:
        text = self._input.text().strip()
        if text:
            self._input.clear()
            self.text_submitted.emit(text)

    def _on_orb_click(self) -> None:
        """Clicking the orb toggles listen or focuses the input."""
        if self._sm.state == AppState.LISTENING:
            self.listen_toggled.emit(False)
        elif not self._sm.is_busy():
            self.listen_toggled.emit(True)
        else:
            self._input.setFocus()

    def _on_mic_toggle(self, checked: bool) -> None:
        self.listen_toggled.emit(checked)

    def _on_alt_space(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        if not self._sm.is_busy():
            self._input.setFocus()
            self._input.selectAll()

    # ── Overlay toggles ───────────────────────────────────────────────────────
    def _toggle_settings(self) -> None:
        if self._settings_ov.isVisible():
            self._settings_ov.hide()
        else:
            self._settings_ov.show()
            self._reposition_overlay(self._settings_ov)

    def _toggle_diagnostics(self) -> None:
        if self._diagnostics.isVisible():
            self._diagnostics.hide()
        else:
            from app.config import print_status, gemini, elevenlabs, ollama
            lines = [
                "VEXION Diagnostics",
                "──────────────────────────────",
                f"Gemini     : {gemini.status()}",
                f"ElevenLabs : {elevenlabs.status()}",
                f"Ollama     : {ollama.status()}",
                "",
                "Shortcuts:",
                "  Alt+Space  — focus / listen",
                "  Ctrl+,     — settings",
                "  Ctrl+D     — diagnostics",
                "  Escape     — toggle full-screen",
                "  Ctrl+Q     — quit",
            ]
            self._diagnostics.show_diagnostics("\n".join(lines))
            self._reposition_overlay(self._diagnostics)

    def _on_escape(self) -> None:
        if self._fullscreen:
            self.showNormal()
            self._fullscreen = False
        else:
            self.showFullScreen()
            self._fullscreen = True

    # ── Public helpers for the assistant core ─────────────────────────────────
    def show_response(self, text: str) -> None:
        """Show a brief assistant response in the state label area."""
        # Truncate long responses for on-screen display
        display = text if len(text) <= 120 else text[:117] + "…"
        self._state_label.setText(display)

    def set_online_status(self, online: bool) -> None:
        if online:
            self._online_dot.setText("● ONLINE")
            self._online_dot.setStyleSheet(
                f"color: rgb({Colors.STATE_ONLINE.red()},"
                f"{Colors.STATE_ONLINE.green()},"
                f"{Colors.STATE_ONLINE.blue()}); letter-spacing: 2px;"
            )
        else:
            self._set_offline_indicator()

    # ── Background painting (stars/gradient) ─────────────────────────────────
    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Deep background gradient
        grad = QLinearGradient(w / 2, 0, w / 2, h)
        grad.setColorAt(0.0,  Colors.BG_DEEP)
        grad.setColorAt(0.55, Colors.BG_MID)
        grad.setColorAt(1.0,  Colors.BG_DEEP)
        p.fillRect(0, 0, w, h, QBrush(grad))

        # Very faint horizon glow at the vertical centre
        from PySide6.QtGui import QRadialGradient
        hglow = QRadialGradient(w / 2, h * 0.52, w * 0.55)
        hglow.setColorAt(0.0, QColor(0, 30, 80, 18))
        hglow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(hglow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(0, 0, w, h)

        p.end()
