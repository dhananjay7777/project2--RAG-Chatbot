"""Groq LLM configuration (from config.yaml + environment)."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from core.settings import load_settings
from policy import ROOT

load_dotenv(ROOT / ".env")

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TIER2_MODEL = "llama-3.1-8b-instant"


def groq_api_key() -> str:
    return os.getenv("GROQ_API_KEY", "").strip()


def generation_model() -> str:
    gen = load_settings().get("generation") or {}
    return str(os.getenv("GROQ_MODEL") or gen.get("model") or DEFAULT_GROQ_MODEL)


def tier2_model() -> str:
    router = load_settings().get("router") or {}
    return str(
        os.getenv("GROQ_TIER2_MODEL")
        or router.get("tier2_model")
        or DEFAULT_TIER2_MODEL
    )


def llm_provider() -> str:
    llm = load_settings().get("llm") or {}
    return str(llm.get("provider") or "groq")
