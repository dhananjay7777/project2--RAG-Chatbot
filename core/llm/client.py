"""Groq chat completions for router Tier-2 and generative synthesis."""

from __future__ import annotations

from typing import Any

from core.llm.config import generation_model, groq_api_key, tier2_model


class GroqConfigurationError(RuntimeError):
    pass


def _client():
    api_key = groq_api_key()
    if not api_key:
        raise GroqConfigurationError("GROQ_API_KEY is not configured")
    try:
        from groq import Groq
    except ImportError as exc:
        raise GroqConfigurationError("groq package is not installed") from exc
    return Groq(api_key=api_key)


def chat_complete(
    *,
    system: str,
    user: str,
    temperature: float = 0,
    model: str | None = None,
    response_format_json: bool = False,
) -> str:
    if temperature != 0:
        raise ValueError("Groq calls in this project require temperature=0")
    client = _client()
    kwargs: dict[str, Any] = {
        "model": model or generation_model(),
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if response_format_json:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return (resp.choices[0].message.content or "").strip()


def tier2_chat_complete(*, system: str, user: str) -> str:
    return chat_complete(
        system=system,
        user=user,
        temperature=0,
        model=tier2_model(),
        response_format_json=True,
    )


def is_groq_configured() -> bool:
    return bool(groq_api_key())
