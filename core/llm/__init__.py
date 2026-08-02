"""Groq LLM integration (Phase 4 Tier-2 + Phase 5 synthesis)."""

from core.llm.client import chat_complete, is_groq_configured, tier2_chat_complete
from core.llm.config import generation_model, groq_api_key, llm_provider, tier2_model

__all__ = [
    "chat_complete",
    "tier2_chat_complete",
    "is_groq_configured",
    "generation_model",
    "tier2_model",
    "groq_api_key",
    "llm_provider",
]
