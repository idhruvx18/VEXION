"""
app/ai/gemini_provider.py
──────────────────────────
Google Gemini cloud AI provider for VEXION.

Uses google-generativeai SDK.
API key is read from config — never printed or logged.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from app.ai.base import AIProvider, GenerateResult, Message
from app.config import gemini as gemini_cfg

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self) -> None:
        self._model_name = gemini_cfg.model
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        if not gemini_cfg.is_configured:
            return
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=gemini_cfg.api_key)
            self._client = genai.GenerativeModel(self._model_name)
        except ImportError:
            logger.warning("google-generativeai not installed — Gemini disabled.")
        except Exception as exc:
            logger.error("Gemini init error (no key details logged): %s", type(exc).__name__)

    # ── Availability ─────────────────────────────────────────────────────────
    def is_available(self) -> bool:
        return self._client is not None and gemini_cfg.is_configured

    # ── Sync generation ───────────────────────────────────────────────────────
    def generate(self, messages: list[Message], **kwargs) -> GenerateResult:
        if not self.is_available():
            hint = (
                "Gemini not configured. Add GEMINI_API_KEY and GEMINI_MODEL to .env."
                if not gemini_cfg.is_configured
                else "Gemini client failed to initialise — check your API key."
            )
            return GenerateResult(
                text="", provider=self.name, model=self._model_name, error=hint
            )

        # Build a simple prompt from message history
        prompt_parts = []
        for m in messages:
            if m.role == "system":
                prompt_parts.append(f"[System]: {m.content}")
            elif m.role == "user":
                prompt_parts.append(f"User: {m.content}")
            elif m.role == "assistant":
                prompt_parts.append(f"VEXION: {m.content}")
        full_prompt = "\n".join(prompt_parts)

        try:
            response = self._client.generate_content(full_prompt)
            text = response.text if hasattr(response, "text") else str(response)
            return GenerateResult(text=text, provider=self.name, model=self._model_name)
        except Exception as exc:
            # Do NOT log exc details that might contain key material
            logger.error("Gemini generate error: %s", type(exc).__name__)
            return GenerateResult(
                text="",
                provider=self.name,
                model=self._model_name,
                error=f"Gemini request failed ({type(exc).__name__}). Check your key and model.",
            )

    # ── Async streaming (wraps sync for now) ─────────────────────────────────
    async def generate_async(
        self, messages: list[Message], **kwargs
    ) -> AsyncIterator[str]:
        result = self.generate(messages, **kwargs)
        if result.ok:
            yield result.text
        else:
            yield f"[Gemini error: {result.error}]"

    # ── Diagnostics ──────────────────────────────────────────────────────────
    def diagnostics(self) -> dict:
        return {
            "provider":     self.name,
            "model":        self._model_name,
            "configured":   gemini_cfg.is_configured,
            "available":    self.is_available(),
            "key_status":   gemini_cfg.status(),   # masked — safe to display
        }
