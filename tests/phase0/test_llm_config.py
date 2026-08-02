"""Groq LLM configuration tests."""

from core.llm.config import DEFAULT_GROQ_MODEL, llm_provider


def test_llm_provider_is_groq():
    assert llm_provider() == "groq"


def test_default_generation_model_is_groq_llama():
    assert "llama" in DEFAULT_GROQ_MODEL
