"""
app/ui/theme.py
───────────────
VEXION visual theme constants.
All colours, fonts, and animation timing live here so they can be
changed in one place.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont


# ── Palette ──────────────────────────────────────────────────────────────────
class Colors:
    # Backgrounds
    BG_DEEP       = QColor(4,   6,  16)      # near-black midnight
    BG_MID        = QColor(6,  10,  28)      # midnight navy
    BG_HORIZON    = QColor(8,  18,  48)      # faint horizon glow

    # Orb / accent
    ORB_CORE      = QColor(0, 200, 255)      # electric cyan
    ORB_MID       = QColor(20, 120, 220)     # mid-blue
    ORB_OUTER     = QColor(60,  40, 140)     # deep violet
    ORB_GLOW      = QColor(0, 160, 255,  60) # translucent glow layer
    ARC_CYAN      = QColor(0, 220, 255, 180)
    ARC_VIOLET    = QColor(140, 60, 255, 120)

    # Text
    TEXT_PRIMARY  = QColor(220, 240, 255)    # near-white cool
    TEXT_DIM      = QColor(100, 140, 180)    # muted blue-grey
    TEXT_ACCENT   = QColor(0,   200, 255)    # cyan accent

    # State indicators
    STATE_ONLINE  = QColor(0,   220, 140)    # green-teal
    STATE_OFFLINE = QColor(220, 60,  60)     # muted red
    STATE_WARN    = QColor(255, 180,  40)    # amber

    # Overlay / glass
    GLASS_BG      = QColor(10,  20,  50, 180)
    GLASS_BORDER  = QColor(0,  160, 255,  60)

    # Waveform
    WAVE_COLOR    = QColor(0,  200, 255, 200)

    # Danger / confirm
    DANGER        = QColor(220, 60,  60)
    CONFIRM_OK    = QColor(0,  200, 140)


# ── Typography ────────────────────────────────────────────────────────────────
class Fonts:
    # System font fallback chain — no external downloads required
    _FAMILY = "Segoe UI"          # Windows default; elegant, legible

    @staticmethod
    def wordmark(size: int = 36) -> QFont:
        f = QFont(Fonts._FAMILY, size, QFont.Weight.Thin)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 12)
        return f

    @staticmethod
    def tagline(size: int = 11) -> QFont:
        f = QFont(Fonts._FAMILY, size, QFont.Weight.Light)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6)
        return f

    @staticmethod
    def state_label(size: int = 13) -> QFont:
        f = QFont(Fonts._FAMILY, size, QFont.Weight.Light)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4)
        return f

    @staticmethod
    def hud(size: int = 9) -> QFont:
        f = QFont(Fonts._FAMILY, size, QFont.Weight.Light)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        return f

    @staticmethod
    def command_input(size: int = 14) -> QFont:
        return QFont(Fonts._FAMILY, size, QFont.Weight.Normal)

    @staticmethod
    def overlay_title(size: int = 16) -> QFont:
        f = QFont(Fonts._FAMILY, size, QFont.Weight.Light)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        return f

    @staticmethod
    def button(size: int = 11) -> QFont:
        f = QFont(Fonts._FAMILY, size, QFont.Weight.Normal)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        return f


# ── Animation timing (ms) ─────────────────────────────────────────────────────
class Timing:
    ORB_PULSE_IDLE      = 3000    # idle gentle pulse period
    ORB_PULSE_LISTEN    = 1400    # listening faster pulse
    ORB_PULSE_THINK     = 2000    # thinking rotation
    ORB_PULSE_SPEAK     = 800     # speaking fast pulse
    WAVE_FRAME          = 40      # waveform redraw interval
    STATE_FADE          = 300     # state label fade duration
    STAR_TWINKLE        = 6000    # star twinkle period
    ARC_ROTATION        = 8000    # arc full rotation period


# ── Sizes (logical pixels — scaled by Qt) ────────────────────────────────────
class Sizes:
    ORB_DIAMETER        = 320     # design baseline; scales with window
    ORB_MIN_DIAMETER    = 180
    WAVEFORM_HEIGHT     = 48
    WAVEFORM_WIDTH      = 340
    INPUT_HEIGHT        = 44
    INPUT_WIDTH         = 520
    OVERLAY_WIDTH       = 500
    OVERLAY_HEIGHT      = 260
