"""
tests/test_config.py
─────────────────────
Tests for the configuration module.
Verifies that missing API keys produce graceful degradation,
not crashes, and that keys are never printed in full.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch
import os


class TestGeminiConfig:
    def test_not_configured_when_key_missing(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            # Re-import to pick up patched env
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert not cfg.gemini.is_configured

    def test_status_shows_not_configured(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            status = cfg.gemini.status()
            assert "Not configured" in status

    def test_key_not_in_status(self):
        fake_key = "AIzaSyFakeKeyForTestingOnly123456789"
        with patch.dict(os.environ, {"GEMINI_API_KEY": fake_key}):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            status = cfg.gemini.status()
            # Full key must not appear
            assert fake_key not in status
            # Should show masked suffix only
            assert "Configured" in status


class TestElevenLabsConfig:
    def test_not_configured_when_keys_missing(self):
        with patch.dict(os.environ, {
            "ELEVENLABS_API_KEY":  "",
            "ELEVENLABS_VOICE_ID": "",
        }, clear=False):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert not cfg.elevenlabs.is_configured

    def test_partially_configured_no_voice_id(self):
        with patch.dict(os.environ, {
            "ELEVENLABS_API_KEY":  "el_test_key",
            "ELEVENLABS_VOICE_ID": "",
        }, clear=False):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert not cfg.elevenlabs.is_configured
            assert "VOICE_ID" in cfg.elevenlabs.status().upper() or "voice" in cfg.elevenlabs.status().lower()

    def test_key_never_printed_full(self):
        fake_key = "el_SomeVeryLongFakeKeyThatShouldNeverAppear"
        with patch.dict(os.environ, {
            "ELEVENLABS_API_KEY":  fake_key,
            "ELEVENLABS_VOICE_ID": "some_voice_id",
        }, clear=False):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            status = cfg.elevenlabs.status()
            assert fake_key not in status


class TestMissingEnvHints:
    def test_hints_present_when_both_missing(self):
        with patch.dict(os.environ, {
            "GEMINI_API_KEY":      "",
            "ELEVENLABS_API_KEY":  "",
            "ELEVENLABS_VOICE_ID": "",
        }, clear=False):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            hints = cfg.get_missing_env_hints()
            assert len(hints) >= 2

    def test_no_crash_on_missing_all_keys(self):
        """App must not crash when all optional keys are absent."""
        with patch.dict(os.environ, {
            "GEMINI_API_KEY":      "",
            "ELEVENLABS_API_KEY":  "",
            "ELEVENLABS_VOICE_ID": "",
            "OLLAMA_MODEL":        "qwen2.5:3b",
        }, clear=False):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            # Should be safe to call
            cfg.print_status()
