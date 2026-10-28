"""
main.py
────────
VEXION application entry point.

Usage:
    python main.py
    python main.py --windowed      (skip full-screen, useful for dev)
    python main.py --diagnostics   (print config status and exit)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def _setup_logging() -> None:
    from app.config import app as app_cfg
    level = getattr(logging, app_cfg.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="VEXION AI Desktop Assistant")
    p.add_argument("--windowed",    action="store_true", help="Launch in window mode")
    p.add_argument("--diagnostics", action="store_true", help="Print config and exit")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    _setup_logging()

    if args.diagnostics:
        from app.config import print_status, get_missing_env_hints
        print_status()
        hints = get_missing_env_hints()
        if hints:
            print("\n⚠️  Setup hints:")
            for h in hints:
                print(f"   • {h}")
        return 0

    # Warn about missing .env
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(
            "\n⚠️  No .env file found.\n"
            "   Copy .env.example → .env and fill in your keys for full functionality.\n"
            "   VEXION will launch in limited mode.\n"
        )

    # PySide6 app
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("VEXION")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("VEXION")

    # High-DPI is enabled by default in PySide6 6.x
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    # Create assistant and main window
    from app.core.assistant import Assistant
    from app.ui.main_window import MainWindow

    assistant = Assistant()
    window    = MainWindow(state_manager=assistant.state_manager)

    # ── Wire signals ──────────────────────────────────────────────────────────
    # User → assistant
    window.text_submitted.connect(assistant.handle_input)
    window.approval_given.connect(assistant.on_approval_given)
    window.approval_cancelled.connect(assistant.on_approval_cancelled)

    # Assistant → UI
    assistant.response_ready.connect(window.show_response)
    assistant.tool_needs_approval.connect(
        lambda pa: window._sm.set_needs_approval(pa.request.description)
    )
    assistant.state_changed.connect(window._on_state_change)

    # Settings changes
    window.settings_changed.connect(_apply_settings)

    # Start microphone listener toggle
    def _on_listen_toggle(start: bool) -> None:
        from app.voice.stt import STTManager
        if start:
            assistant.state_manager.set_listening()
            if not hasattr(app, "_stt"):
                app._stt = STTManager()
            app._stt.start(
                on_result=assistant.handle_input,
                on_error=lambda e: assistant.state_manager.set_error(e),
            )
        else:
            if hasattr(app, "_stt"):
                app._stt.stop()
            if assistant.state_manager.state.name == "LISTENING":
                assistant.state_manager.set_idle()

    window.listen_toggled.connect(_on_listen_toggle)

    if args.windowed:
        window.showNormal()

    window.show()
    return app.exec()


def _apply_settings(settings: dict) -> None:
    from app.config import app as app_cfg
    app_cfg.voice_enabled  = settings.get("voice_input", True)
    app_cfg.cloud_enabled  = settings.get("cloud_ai", True)


if __name__ == "__main__":
    sys.exit(main())
