"""LLM client for generative synthesis (Groq)."""

from __future__ import annotations

from typing import Protocol

from core.llm.config import generation_model
from core.llm.client import GroqConfigurationError, chat_complete


class ChatCompleter(Protocol):
    def complete(self, *, system: str, user: str, temperature: float) -> str: ...


class GroqChatCompleter:
    def __init__(self, *, model: str | None = None) -> None:
        self._model = model or generation_model()

    def complete(self, *, system: str, user: str, temperature: float) -> str:
        try:
            return chat_complete(
                system=system,
                user=user,
                temperature=temperature,
                model=self._model,
            )
        except GroqConfigurationError as exc:
            raise RuntimeError(str(exc)) from exc
