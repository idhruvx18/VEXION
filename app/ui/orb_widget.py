"""
app/ui/orb_widget.py
─────────────────────
VEXION holographic orb — the main visual centrepiece.

Drawn entirely with QPainter (no external images required).
Layers:
  1. Outer diffuse glow (radial gradient, large)
  2. Energy rings / orbiting arcs (state-dependent rotation)
  3. Mid sphere (radial gradient cyan → violet)
  4. Inner core highlight
  5. Subtle vertical light beam (idle/speaking)

All animation runs on QTimers — no blocking calls.
Reduced-motion: when VEXION_REDUCED_MOTION=1 env var is set,
animations are replaced with static rendering.
"""

from __future__ import annotations

import math
import os
import time

from PySide6.QtCore import (
    QPointF, QRectF, QTimer, Qt, QPropertyAnimation,
    QEasingCurve, Property, Signal
)
from PySide6.QtGui import (
    QColor, QConicalGradient, QPainter, QPainterPath,
    QPen, QRadialGradient, QLinearGradient, QBrush
)
from PySide6.QtWidgets import QWidget

from app.core.state import AppState
from app.ui.theme import Colors, Timing, Sizes


_REDUCED_MOTION = os.environ.get("VEXION_REDUCED_MOTION", "0") == "1"


class OrbWidget(QWidget):
    """Animated holographic orb widget."""

    clicked = Signal()          # emitted when user clicks the orb

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state: AppState = AppState.IDLE
        self._arc_angle: float = 0.0        # degrees, for rotating arcs
        self._pulse_phase: float = 0.0      # 0..1 for glow pulsing
        self._beam_phase: float = 0.0       # 0..1 for beam flicker
        self._wave_values: list[float] = [0.5] * 32
        self._wave_pos: int = 0

        self.setMinimumSize(Sizes.ORB_MIN_DIAMETER, Sizes.ORB_MIN_DIAMETER)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        if not _REDUCED_MOTION:
            self._anim_timer = QTimer(self)
            self._anim_timer.timeout.connect(self._tick)
            self._anim_timer.start(16)          # ~60 fps

    # ── Public API ───────────────────────────────────────────────────────────
    def set_state(self, state: AppState) -> None:
        self._state = state
        self.update()

    def push_wave_sample(self, level: float) -> None:
        """Feed a normalised [0..1] amplitude sample for the waveform."""
        self._wave_values[self._wave_pos % len(self._wave_values)] = level
        self._wave_pos += 1

    # ── Animation tick ────────────────────────────────────────────────────────
    def _tick(self) -> None:
        now = time.monotonic()
        period = self._arc_period()
        self._arc_angle = (now % period) / period * 360.0
        self._pulse_phase = (math.sin(now * (2 * math.pi / (self._pulse_period() / 1000))) + 1) / 2
        self._beam_phase  = (math.sin(now * 1.3) + 1) / 2
        self.update()

    def _arc_period(self) -> float:
        """Arc rotation period in seconds."""
        if self._state == AppState.THINKING:
            return Timing.ORB_PULSE_THINK / 1000
        if self._state == AppState.LISTENING:
            return Timing.ORB_PULSE_LISTEN / 1000
        return Timing.ARC_ROTATION / 1000

    def _pulse_period(self) -> int:
        if self._state == AppState.LISTENING:
            return Timing.ORB_PULSE_LISTEN
        if self._state == AppState.SPEAKING:
            return Timing.ORB_PULSE_SPEAK
        if self._state == AppState.THINKING:
            return Timing.ORB_PULSE_THINK
        return Timing.ORB_PULSE_IDLE

    # ── Qt events ─────────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    # ── Painting ─────────────────────────────────────────────────────────────
    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) * 0.44        # orb radius = 44 % of smaller dimension

        self._draw_outer_glow(painter, cx, cy, r)
        self._draw_rings(painter, cx, cy, r)
        self._draw_orb(painter, cx, cy, r)
        self._draw_core_highlight(painter, cx, cy, r)
        if self._state in (AppState.IDLE, AppState.SPEAKING):
            self._draw_beam(painter, cx, cy, r)
        painter.end()

    def _draw_outer_glow(self, p: QPainter, cx, cy, r) -> None:
        glow_r = r * 1.9
        grad = QRadialGradient(cx, cy, glow_r)
        alpha = int(30 + self._pulse_phase * 30)

        if self._state == AppState.ERROR or self._state == AppState.OFFLINE:
            base = QColor(180, 30, 30, alpha)
            mid  = QColor(100, 20, 20, alpha // 2)
        elif self._state == AppState.LISTENING:
            base = QColor(0, 220, 255, alpha + 20)
            mid  = QColor(0, 160, 255, alpha // 2)
        elif self._state == AppState.THINKING:
            base = QColor(120, 60, 255, alpha)
            mid  = QColor(60, 30, 180, alpha // 2)
        else:
            base = QColor(0, 160, 255, alpha)
            mid  = QColor(40, 40, 140, alpha // 2)

        grad.setColorAt(0.0, base)
        grad.setColorAt(0.5, mid)
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2))

    def _draw_rings(self, p: QPainter, cx, cy, r) -> None:
        if _REDUCED_MOTION:
            return

        # Outer arc ring — slow rotation
        ring_r = r * 1.28
        pen = QPen(Colors.ARC_CYAN, 1.0, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        angle = self._arc_angle
        span  = 200 if self._state == AppState.THINKING else 120
        p.drawArc(
            QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2),
            int(angle * 16), int(span * 16)
        )

        # Inner arc ring — counter-rotation
        ring_r2 = r * 1.12
        pen2 = QPen(Colors.ARC_VIOLET, 1.0, Qt.PenStyle.SolidLine)
        pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen2)
        angle2 = -(angle * 1.4) % 360
        span2  = 160 if self._state == AppState.THINKING else 80
        p.drawArc(
            QRectF(cx - ring_r2, cy - ring_r2, ring_r2 * 2, ring_r2 * 2),
            int(angle2 * 16), int(span2 * 16)
        )

        # Executing: progress ring
        if self._state == AppState.EXECUTING:
            ring_r3 = r * 1.4
            pen3 = QPen(Colors.STATE_WARN, 1.5, Qt.PenStyle.SolidLine)
            p.setPen(pen3)
            progress_span = int((self._pulse_phase * 360) * 16)
            p.drawArc(
                QRectF(cx - ring_r3, cy - ring_r3, ring_r3 * 2, ring_r3 * 2),
                90 * 16, -progress_span
            )

    def _draw_orb(self, p: QPainter, cx, cy, r) -> None:
        pulse = self._pulse_phase

        if self._state == AppState.ERROR or self._state == AppState.OFFLINE:
            c_inner = QColor(200, 60, 60)
            c_mid   = QColor(100, 20, 20)
            c_outer = QColor(40,  10, 10)
        elif self._state == AppState.LISTENING:
            brightness = int(220 + pulse * 35)
            c_inner = QColor(0, brightness, 255)
            c_mid   = QColor(0, 100, 220)
            c_outer = QColor(20, 30, 100)
        elif self._state == AppState.THINKING:
            c_inner = QColor(100, 80, 255)
            c_mid   = QColor(60,  40, 200)
            c_outer = QColor(20,  10,  80)
        elif self._state == AppState.SPEAKING:
            brightness = int(180 + pulse * 75)
            c_inner = QColor(0, brightness, 255)
            c_mid   = QColor(0, 80, 200)
            c_outer = QColor(10, 20, 80)
        else:
            # Idle — soft glow
            alpha_shift = int(pulse * 20)
            c_inner = QColor(0, 180 + alpha_shift, 255)
            c_mid   = QColor(0, 80,  200)
            c_outer = QColor(10, 20,  80)

        grad = QRadialGradient(cx - r * 0.2, cy - r * 0.25, r * 1.2)
        grad.setColorAt(0.0,  c_inner)
        grad.setColorAt(0.45, c_mid)
        grad.setColorAt(1.0,  c_outer)

        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(0, 160, 255, 80), 1.0))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

    def _draw_core_highlight(self, p: QPainter, cx, cy, r) -> None:
        # Small bright specular highlight top-left
        hr = r * 0.35
        hx = cx - r * 0.28
        hy = cy - r * 0.30
        grad = QRadialGradient(hx, hy, hr)
        grad.setColorAt(0.0, QColor(255, 255, 255, 100))
        grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(hx - hr, hy - hr, hr * 2, hr * 2))

    def _draw_beam(self, p: QPainter, cx, cy, r) -> None:
        """Subtle vertical light column above the orb."""
        alpha = int(20 + self._beam_phase * 25)
        beam_h = r * 2.0
        beam_w = r * 0.06
        grad = QLinearGradient(cx, cy - r, cx, cy - r - beam_h)
        grad.setColorAt(0.0, QColor(0, 200, 255, alpha))
        grad.setColorAt(1.0, QColor(0, 200, 255, 0))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(QRectF(cx - beam_w / 2, cy - r - beam_h, beam_w, beam_h))
