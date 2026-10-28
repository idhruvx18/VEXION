"""
app/ai/base.py
──────────────
Abstract base class for all VEXION AI providers.
Each provider must implement `generate` (sync) and `generate_async`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class Message:
    role: str           # "user" | "assistant" | "system"
    content: str


@dataclass
class GenerateResult:
    text: str
    provider: str
    model: str
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class AIProvider(ABC):
    """Base class for all AI providers."""

    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider can currently handle requests."""

    @abstractmethod
    def generate(self, messages: list[Message], **kwargs) -> GenerateResult:
        """Synchronous generation (runs in a worker thread)."""

    @abstractmethod
    async def generate_async(
        self, messages: list[Message], **kwargs
    ) -> AsyncIterator[str]:
        """Async streaming generation."""

    def diagnostics(self) -> dict:
        """Return a dict of status information for the diagnostics panel."""
        return {"provider": self.name, "available": self.is_available()}
