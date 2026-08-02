"""UI → pipeline adapter. In-process by default, HTTP when MF_API_URL is set."""

from __future__ import annotations

import logging
import os
from typing import Any

from app.ui.presenter import AnswerView, envelope_to_view, error_view
from schemas.answer import AnswerEnvelope

logger = logging.getLogger(__name__)

GENERIC_ERROR = (
    "The assistant could not complete that lookup just now. "
    "Try again, or ask about a different scheme detail."
)


def _via_http(query: str, base_url: str) -> AnswerEnvelope:
    import requests

    response = requests.post(
        f"{base_url.rstrip('/')}/ask",
        json={"query": query},
        timeout=30,
    )
    response.raise_for_status()
    return AnswerEnvelope.model_validate(response.json())


def answer(query: str) -> AnswerView:
    """Run the full pipeline and return a render-ready view, never raising."""

    base_url = os.getenv("MF_API_URL", "").strip()
    try:
        if base_url:
            envelope = _via_http(query, base_url)
        else:
            from core.ask import ask

            envelope = ask(query)
    except Exception:  # noqa: BLE001 — the UI must never surface a stack trace
        logger.exception("ask pipeline failed")
        return error_view(GENERIC_ERROR)
    return envelope_to_view(envelope)


def envelope_payload(envelope: AnswerEnvelope) -> dict[str, Any]:
    return envelope.model_dump(mode="json")
