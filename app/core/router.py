"""
app/core/router.py
──────────────────
VEXION AI provider router.

Routing rules:
  1. If Gemini is configured and cloud_enabled → use Gemini (primary cloud).
  2. If Gemini fails or is not configured → fall back to Ollama.
  3. If neither is available → return a helpful offline message.

Privacy rule:
  - Cloud requests are made only when app.config.app.cloud_enabled is True.
  - The router never automatically includes file content or credentials.
"""

from __future__ import annotations

import logging

from app.ai.base import AIProvider, GenerateResult, Message
from app.ai.gemini_provider import GeminiProvider
from app.ai.ollama_provider import OllamaProvider
from app.config import app as app_cfg

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are VEXION, a personal desktop AI assistant for Windows.
You are direct, helpful, and concise.
You can help the user open apps, browse the web, search files, tell the time,
create notes, and answer questions.
When you need to use a tool, respond ONLY with a JSON block like:
  {"tool": "tool_name", "args": {"key": "value"}}
Otherwise respond naturally in plain text.
Keep responses short and conversational — this is a voice interface.
"""


class ProviderRouter:
    """Routes AI requests to the best available provider."""

    def __init__(self) -> None:
        self._gemini = GeminiProvider()
        self._ollama = OllamaProvider()

    # ── Provider selection ────────────────────────────────────────────────────
    def _primary(self) -> AIProvider | None:
        if app_cfg.cloud_enabled and self._gemini.is_available():
            return self._gemini
        return None

    def _fallback(self) -> AIProvider | None:
        if self._ollama.is_available():
            return self._ollama
        return None

    def best_provider(self) -> AIProvider | None:
        return self._primary() or self._fallback()

    # ── Generate ──────────────────────────────────────────────────────────────
    def generate(self, user_text: str, history: list[Message] | None = None) -> GenerateResult:
        messages: list[Message] = [Message(role="system", content=_SYSTEM_PROMPT)]
        if history:
            messages.extend(history)
        messages.append(Message(role="user", content=user_text))

        provider = self._primary()
        if provider:
            result = provider.generate(messages)
            if result.ok:
                return result
            # Primary failed — log type only, not content
            logger.warning("Primary provider failed (%s), falling back.", provider.name)

        fallback = self._fallback()
        if fallback:
            result = fallback.generate(messages)
            if result.ok:
                logger.info("Using fallback provider: %s", fallback.name)
            return result

        return GenerateResult(
            text=(
                "No AI provider is available right now.\n\n"
                "• For local AI: make sure Ollama is running (`ollama serve`) "
                f"and the model '{self._ollama._model}' is installed (`ollama pull {self._ollama._model}`).\n"
                "• For cloud AI: add GEMINI_API_KEY to your .env file."
            ),
            provider="none",
            model="none",
            error="No provider available",
        )

    # ── Diagnostics ──────────────────────────────────────────────────────────
    def diagnostics(self) -> dict:
        return {
            "cloud_enabled":   app_cfg.cloud_enabled,
            "active_provider": (p.name if (p := self.best_provider()) else "none"),
            "gemini":          self._gemini.diagnostics(),
            "ollama":          self._ollama.diagnostics(),
        }
