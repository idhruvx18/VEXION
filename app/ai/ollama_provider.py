"""
app/ai/ollama_provider.py
──────────────────────────
Ollama local AI provider for VEXION.

Communicates with the Ollama HTTP API (default http://localhost:11434).
Falls back gracefully when Ollama is not running.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

from app.ai.base import AIProvider, GenerateResult, Message
from app.config import ollama as ollama_cfg

logger = logging.getLogger(__name__)

_TIMEOUT = 60.0          # seconds; local models can be slow on first token


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self) -> None:
        self._base_url = ollama_cfg.base_url.rstrip("/")
        self._model    = ollama_cfg.model

    # ── Availability ─────────────────────────────────────────────────────────
    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self._base_url}/api/tags", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def model_installed(self) -> bool:
        """Return True if the configured model is in `ollama list`."""
        try:
            r = httpx.get(f"{self._base_url}/api/tags", timeout=3.0)
            if r.status_code != 200:
                return False
            data = r.json()
            names = [m.get("name", "") for m in data.get("models", [])]
            return any(self._model in n for n in names)
        except Exception:
            return False

    # ── Sync generation ───────────────────────────────────────────────────────
    def generate(self, messages: list[Message], **kwargs) -> GenerateResult:
        if not self.is_available():
            return GenerateResult(
                text="",
                provider=self.name,
                model=self._model,
                error="Ollama is not running. Start it with: ollama serve",
            )

        payload = {
            "model":    self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream":   False,
        }
        try:
            r = httpx.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            text = data.get("message", {}).get("content", "")
            return GenerateResult(text=text, provider=self.name, model=self._model)
        except httpx.HTTPStatusError as exc:
            msg = f"Ollama HTTP error {exc.response.status_code}"
            logger.error(msg)
            return GenerateResult(text="", provider=self.name, model=self._model, error=msg)
        except Exception as exc:
            logger.error("Ollama generate error: %s", exc)
            return GenerateResult(text="", provider=self.name, model=self._model, error=str(exc))

    # ── Async streaming ───────────────────────────────────────────────────────
    async def generate_async(
        self, messages: list[Message], **kwargs
    ) -> AsyncIterator[str]:
        payload = {
            "model":    self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream":   True,
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                async with client.stream(
                    "POST", f"{self._base_url}/api/chat", json=payload
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            chunk = data.get("message", {}).get("content", "")
                            if chunk:
                                yield chunk
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            logger.error("Ollama async error: %s", exc)
            yield f"[Ollama error: {exc}]"

    # ── Diagnostics ──────────────────────────────────────────────────────────
    def diagnostics(self) -> dict:
        available = self.is_available()
        return {
            "provider":        self.name,
            "base_url":        self._base_url,
            "model":           self._model,
            "available":       available,
            "model_installed": self.model_installed() if available else False,
        }
